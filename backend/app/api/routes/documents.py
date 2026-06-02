import os
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status, Depends, BackgroundTasks
import uuid

from fastapi.responses import FileResponse
from app.api.routes.insights import generate_insights_task
from app.core.security import get_current_user
import app.services.b2_service as b2_service
from app.db.supabase import (
    delete_document,
    find_document_by_filename,
    get_db_connection,
    insert_chunks,
    insert_document,
    get_user_documents,
)
from app.models.document import DuplicateCheckResponse, UploadResponse
from app.services.parser import (
    parse_docx,
    parse_image,
    parse_pdf,
    parse_xlsx,
)

router = APIRouter(prefix="/documents", tags=["Documents"])

# ---------------------------------------------------------------------------
# Supported file types and the MIME types that map to each parser
# ---------------------------------------------------------------------------
SUPPORTED_TYPES: dict[str, str] = {
    # PDF
    "application/pdf": "pdf",
    # Word
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "docx",
    # Excel
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xlsx",
    # Images
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "image/gif": "image",
    "image/tiff": "image",
}


def _run_parser(file_type: str, tmp_path: str) -> list[dict]:
    """
    Calls the correct parser and normalises the output into a plain list of dicts
    so the DB layer does not need to know about individual Pydantic model types.
    """
    if file_type == "pdf":
        chunks = parse_pdf(tmp_path)
    elif file_type == "docx":
        chunks = parse_docx(tmp_path)
    elif file_type == "xlsx":
        chunks = parse_xlsx(tmp_path)
    elif file_type == "image":
        chunks = parse_image(tmp_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    return [c.model_dump() for c in chunks]


# ---------------------------------------------------------------------------
# GET /documents/check?filename=...
# ---------------------------------------------------------------------------
@router.get(
    "/check",
    response_model=DuplicateCheckResponse,
    summary="Check if a document has already been processed",
    description=(
        "Returns whether a document with the given filename already exists "
        "in the database, along with metadata about the existing record."
    ),
)
def check_duplicate(
    filename: str = Query(..., description="The filename to check for duplicates"),
    user_id: str = Depends(get_current_user),
):
    conn = get_db_connection()
    try:
        existing = find_document_by_filename(conn, user_id, filename)
    finally:
        conn.close()

    if existing is None:
        return DuplicateCheckResponse(exists=False, filename=filename)

    return DuplicateCheckResponse(
        exists=True,
        filename=filename,
        document_id=existing["id"],
        file_type=existing["file_type"],
        chunk_count=existing["chunk_count"],
        created_at=existing["created_at"],
    )


# ---------------------------------------------------------------------------
# POST /documents/upload
# ---------------------------------------------------------------------------
@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document for indexing",
    description=(
        "Upload a PDF, Word (.docx), Excel (.xlsx), or image file. "
        "The file is parsed into text chunks with exact location metadata "
        "(page/line for PDFs, paragraph index for Word, cell reference for Excel, "
        "line number for images) and stored in Supabase for hybrid search."
    ),
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="PDF, DOCX, XLSX, or image file")],
    force_reprocess: bool = Query(
        False,
        description=(
            "If true and the file already exists, the previous data is deleted "
            "and the file is re-processed from scratch."
        ),
    ),
    user_id: str = Depends(get_current_user),
):
    # --- Validate MIME type ------------------------------------------------
    content_type = file.content_type or ""
    file_type = SUPPORTED_TYPES.get(content_type)

    if file_type is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{content_type}'. "
                f"Accepted types: PDF, DOCX, XLSX, JPEG, PNG, WEBP, GIF, TIFF."
            ),
        )

    # --- Check for duplicate (unless force_reprocess is requested) ---------
    conn = get_db_connection()
    try:
        existing = find_document_by_filename(conn, user_id, file.filename or "unknown")

        if existing and not force_reprocess:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        f"'{file.filename}' has already been processed "
                        f"({existing['chunk_count']} segments indexed). "
                        "You can query it now, or re-upload with reprocess enabled."
                    ),
                    "document_id": str(existing["id"]),
                    "chunk_count": existing["chunk_count"],
                },
            )

        # If force_reprocess, delete old data first
        if existing and force_reprocess:
            delete_document(conn, existing["id"], user_id)
            conn.commit()
    finally:
        conn.close()

    # --- Save upload to a temp file so parsers can open it by path ----------
    suffix = Path(file.filename or "upload").suffix or f".{file_type}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # --- Parse the document --------------------------------------------
        chunks = _run_parser(file_type, tmp_path)

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No text could be extracted from the uploaded file.",
            )

        # --- Persist to Supabase -------------------------------------------
        conn = get_db_connection()
        try:
            document_id = insert_document(conn, user_id, file.filename or "unknown", file_type)
            chunks_saved = insert_chunks(conn, document_id, chunks)
            conn.commit()
        except Exception as db_err:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {db_err}",
            ) from db_err
        finally:
            conn.close()

        # --- Upload to Backblaze B2 ----------------------------------------
        try:
            b2_service.upload_file(tmp_path, user_id, str(document_id), file.filename or "unknown")
        except Exception as b2_err:
            # If B2 upload fails, we should ideally rollback DB, but for now we'll just log and fail
            print(f"B2 upload failed: {b2_err}")

    finally:
        # Always delete the temp file even if parsing or DB fails
        os.unlink(tmp_path)

    # Trigger background task to regenerate insights
    background_tasks.add_task(generate_insights_task, user_id)

    return UploadResponse(
        document_id=document_id,
        filename=file.filename or "unknown",
        file_type=file_type,
        chunks_saved=chunks_saved,
        message=f"Successfully indexed {chunks_saved} chunks from '{file.filename}'.",
    )


# ---------------------------------------------------------------------------
# GET /documents
# ---------------------------------------------------------------------------
@router.get(
    "",
    summary="Get user's documents",
    description="Returns a list of all documents uploaded by the authenticated user.",
)
def list_documents(user_id: str = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        docs = get_user_documents(conn, user_id)
        return docs
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# DELETE /documents/{document_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="Deletes a document and its parsed chunks if it belongs to the authenticated user.",
)
def remove_document(
    document_id: uuid.UUID, 
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    conn = get_db_connection()
    try:
        filename = delete_document(conn, document_id, user_id)
        if not filename:
            raise HTTPException(status_code=404, detail="Document not found or unauthorized")
        conn.commit()
        
        # Delete from Backblaze B2
        try:
            b2_service.delete_file(user_id, str(document_id), filename)
        except Exception as e:
            print(f"Error deleting from B2: {e}")
            
        # Regenerate insights after deletion so suggestions don't remain
        background_tasks.add_task(generate_insights_task, user_id)
    except Exception as e:
        conn.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /documents/{document_id}/download
# ---------------------------------------------------------------------------
@router.get(
    "/{document_id}/download",
    summary="Download a document",
    description="Downloads the original file from Backblaze B2.",
)
def download_document(
    document_id: uuid.UUID,
    filename: str = Query(..., description="The filename of the document to download"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user_id: str = Depends(get_current_user)
):
    suffix = Path(filename).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.close()
    
    success = b2_service.download_file(user_id, str(document_id), filename, tmp.name)
    if not success:
        os.unlink(tmp.name)
        raise HTTPException(status_code=404, detail="File not found in storage.")
    
    background_tasks.add_task(os.unlink, tmp.name)
    return FileResponse(path=tmp.name, filename=filename)
