from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.agents.search_agent import run_search_agent, extract_filenames_from_thread
from app.core.security import get_current_user
from app.api.routes.insights import generate_insights_task
from app.db.supabase import get_db_connection, upsert_chat_thread, update_chat_thread_filenames

router = APIRouter(prefix="/search", tags=["Search"])

class SearchRequest(BaseModel):
    query: str
    thread_id: Optional[str] = "default_thread"
    associated_filename: Optional[str] = None

class SearchResponse(BaseModel):
    answer: str

@router.post("", response_model=SearchResponse)
def search(
    request: SearchRequest, 
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """
    Stateful conversational search endpoint.
    Leverages LangGraph checkpointing for follow-up capability.
    """
    try:
        # Generate a brief title from the query if this is the first message (or update it)
        # We just truncate the query for the title
        title = request.query[:50] + "..." if len(request.query) > 50 else request.query
        
        conn = get_db_connection()
        try:
            upsert_chat_thread(
                conn, 
                user_id=user_id, 
                thread_id=request.thread_id, 
                title=title, 
                associated_filename=request.associated_filename
            )
            conn.commit()
        finally:
            conn.close()

        answer = run_search_agent(request.query, request.thread_id, user_id, request.associated_filename)
        
        # After the agent runs, extract all filenames referenced in the thread's tool calls
        extracted_filenames = extract_filenames_from_thread(request.thread_id, user_id)
        
        # Combine explicitly associated filename with extracted ones
        all_filenames = set(extracted_filenames)
        if request.associated_filename:
            # The explicit associated_filename might be a comma-separated list now, so split it
            for fname in request.associated_filename.split(','):
                if fname.strip():
                    all_filenames.add(fname.strip())
        
        if all_filenames:
            combined_filenames = ", ".join(sorted(list(all_filenames)))
            conn2 = get_db_connection()
            try:
                update_chat_thread_filenames(conn2, request.thread_id, combined_filenames)
                conn2.commit()
            finally:
                conn2.close()

        # Trigger background task to regenerate insights
        background_tasks.add_task(generate_insights_task, user_id)
        
        return SearchResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
