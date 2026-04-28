from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from app.core.security import get_current_user
from app.db.supabase import get_db_connection, get_user_chat_threads, delete_chat_thread, delete_all_chat_threads
from app.agents.search_agent import get_thread_messages

router = APIRouter(prefix="/history", tags=["History"])

class ChatThreadResponse(BaseModel):
    thread_id: str
    title: str
    associated_filename: Optional[str] = None
    updated_at: str

class ChatMessage(BaseModel):
    role: str
    content: str

@router.get("", response_model=List[ChatThreadResponse])
def get_history(user_id: str = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        threads = get_user_chat_threads(conn, user_id)
        # Convert datetime to ISO string for JSON serialization
        for t in threads:
            t["updated_at"] = t["updated_at"].isoformat() if t["updated_at"] else ""
        return threads
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/{thread_id}", response_model=List[ChatMessage])
def get_thread_history(thread_id: str, user_id: str = Depends(get_current_user)):
    try:
        messages = get_thread_messages(thread_id, user_id)
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{thread_id}")
def delete_thread(thread_id: str, user_id: str = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        success = delete_chat_thread(conn, user_id, thread_id)
        if not success:
            raise HTTPException(status_code=404, detail="Thread not found")
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.delete("")
def delete_all_history(user_id: str = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        count = delete_all_chat_threads(conn, user_id)
        conn.commit()
        return {"status": "success", "deleted_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
