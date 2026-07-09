from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import FileResponse
import tempfile
import os
from typing import List, Optional
from pydantic import BaseModel
from app.core.security import get_current_user
from app.db.supabase import get_db_connection, get_user_chat_threads, delete_chat_thread, delete_all_chat_threads, insert_document
from app.agents.search_agent import get_thread_messages
from app.utils.export_helper import generate_pdf_export, generate_docx_export
import app.services.b2_service as b2_service

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


@router.post("/{thread_id}/export")
def export_chat_thread(
    thread_id: str,
    format: str = Query(..., description="Export format: 'pdf' or 'docx'"),
    save_to_b2: bool = Query(False, description="Whether to save the file to Backblaze B2"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user_id: str = Depends(get_current_user)
):
    try:
        messages = get_thread_messages(thread_id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch thread messages: {str(e)}")
        
    if not messages:
        raise HTTPException(status_code=400, detail="Cannot export an empty chat history.")
        
    conn = get_db_connection()
    title = "Chat History"
    associated_filename = None
    try:
        threads = get_user_chat_threads(conn, user_id)
        thread_info = next((t for t in threads if t["thread_id"] == thread_id), None)
        if thread_info:
            title = thread_info["title"]
            associated_filename = thread_info["associated_filename"]
    except Exception:
        pass
    finally:
        conn.close()

    import re
    from datetime import datetime
    slug = re.sub(r'[^a-zA-Z0-9_-]', '_', title)
    slug = re.sub(r'_+', '_', slug).strip('_')
    if not slug:
        slug = f"export_{thread_id}"
        
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"chat_{slug}_{date_str}.{format}"
    
    suffix = f".{format}"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_path = tmp.name
    tmp.close()
    
    try:
        if format == "pdf":
            generate_pdf_export(messages, title, associated_filename, tmp_path)
        elif format == "docx":
            generate_docx_export(messages, title, associated_filename, tmp_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format. Use 'pdf' or 'docx'.")
            
        if save_to_b2:
            conn = get_db_connection()
            try:
                document_id = insert_document(conn, user_id, filename, format)
                conn.commit()
            except Exception as db_err:
                conn.rollback()
                raise HTTPException(status_code=500, detail=f"Database error: {db_err}")
            finally:
                conn.close()
                
            try:
                b2_service.upload_file(tmp_path, user_id, str(document_id), filename)
            except Exception as b2_err:
                conn = get_db_connection()
                try:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM documents WHERE id = %s;", (str(document_id),))
                    conn.commit()
                finally:
                    conn.close()
                raise HTTPException(status_code=500, detail=f"Cloud upload failed: {b2_err}")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                
            return {
                "status": "success",
                "message": f"Successfully exported chat to '{filename}' and saved to cloud.",
                "document_id": str(document_id),
                "filename": filename
            }
            
        background_tasks.add_task(os.unlink, tmp_path)
        return FileResponse(path=tmp_path, filename=filename, media_type="application/octet-stream")
        
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Export generation failed: {str(e)}")
