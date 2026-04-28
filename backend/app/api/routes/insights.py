from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from datetime import datetime, timezone, timedelta
import asyncio

from app.core.security import get_current_user
from app.db.supabase import get_db_connection, get_chunks_from_recent_docs, get_cached_insights, upsert_cached_insights
from app.core.config import settings

router = APIRouter(prefix="/insights", tags=["Insights"])

class Insight(BaseModel):
    text: str = Field(description="A brief key insight derived from the documents")
    source_filename: str = Field(description="The exact filename of the document this insight is primarily derived from")

class Suggestion(BaseModel):
    text: str = Field(description="The suggested follow-up question")
    source_filename: str = Field(description="The exact filename of the document this question is primarily derived from")

class InsightsResponse(BaseModel):
    insights: list[Insight] = Field(description="2 brief insights derived from the documents")
    suggestions: list[Suggestion] = Field(description="3 suggested follow-up questions the user could ask")

def generate_insights_task(user_id: str):
    """
    Background task to dynamically generate insights based on the top 5 documents.
    It will skip generation if insights were updated within the last 30 minutes.
    """
    conn = get_db_connection()
    try:
        # Check cache age to avoid excessive LLM calls (30 min limit)
        cached = get_cached_insights(conn, user_id)
        if cached and cached["updated_at"]:
            age = datetime.now(timezone.utc) - cached["updated_at"]
            if age < timedelta(minutes=30):
                return  # Skip, data is still fresh
        
        chunks = get_chunks_from_recent_docs(conn, user_id, doc_limit=5, chunks_per_doc=4)
        if not chunks:
            return

        context_text = "\n\n".join([f"[{c['filename']}]\n{c['content']}" for c in chunks])
        
        llm = ChatOpenAI(
            model=settings.VISION_MODEL_NAME, 
            base_url=settings.VISION_MODEL_URL,
            api_key=settings.VISION_MODEL_API_KEY,
            temperature=0.7
        ).with_structured_output(InsightsResponse)

        prompt = PromptTemplate.from_template(
            "You are an AI assistant analyzing a user's top 5 recently uploaded documents.\n\n"
            "Here is a sample of the text from these documents:\n"
            "---\n{context}\n---\n\n"
            "Based ONLY on this content, generate exactly 2 brief, high-level key insights "
            "(1 sentence each). For each insight, provide the exact filename of the source document "
            "it is derived from. Also generate exactly 3 suggested follow-up questions the user could ask "
            "to learn more. For each question, provide the exact filename of the source document it is derived from. "
            "Ensure everything is highly relevant to the provided text."
        )

        chain = prompt | llm
        result = chain.invoke({"context": context_text})
        
        # Save results to database cache
        upsert_cached_insights(
            conn, 
            user_id, 
            [i.dict() for i in result.insights], 
            [s.dict() for s in result.suggestions]
        )
        conn.commit()
    except Exception as e:
        print(f"Failed to generate insights in background: {e}")
    finally:
        conn.close()

@router.get("", response_model=InsightsResponse)
def get_insights(background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    """
    Fetches the cached insights instantly. If they are stale or missing, 
    it kicks off a background generation task.
    """
    conn = get_db_connection()
    try:
        cached = get_cached_insights(conn, user_id)
        
        # Trigger background regeneration if missing or stale (older than 30 mins)
        needs_regeneration = False
        if not cached:
            needs_regeneration = True
        else:
            age = datetime.now(timezone.utc) - cached["updated_at"]
            if age > timedelta(minutes=30):
                needs_regeneration = True
                
        if needs_regeneration:
            background_tasks.add_task(generate_insights_task, user_id)
            
        if cached:
            return InsightsResponse(
                insights=cached["insights"],
                suggestions=cached["suggestions"]
            )
        
        # If no cache exists yet, return empty arrays so the UI doesn't break.
        # It will populate on next reload after background task finishes.
        return InsightsResponse(insights=[], suggestions=[])
    finally:
        conn.close()
