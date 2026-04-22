from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agents.search_agent import run_search_agent

router = APIRouter(prefix="/search", tags=["Search"])

class SearchRequest(BaseModel):
    query: str
    thread_id: str

class SearchResponse(BaseModel):
    answer: str

@router.post("/", response_model=SearchResponse)
def perform_search(request: SearchRequest):
    """
    Takes a natural language or keyword query, triggers the LangGraph agent,
    and returns a synthesized answer with citations to the documents.
    """
    try:
        answer = run_search_agent(request.query, request.thread_id)
        return SearchResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
