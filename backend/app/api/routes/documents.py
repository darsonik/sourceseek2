import os
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.db.supabase import get_db_connection, insert_chunks, insert_document
from app.models.document import UploadResponse
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
    file: Annotated[UploadFile, File(description="PDF, DOCX, XLSX, or image file")],
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
            document_id = insert_document(conn, file.filename or "unknown", file_type)
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

    finally:
        # Always delete the temp file even if parsing or DB fails
        os.unlink(tmp_path)

    return UploadResponse(
        document_id=document_id,
        filename=file.filename or "unknown",
        file_type=file_type,
        chunks_saved=chunks_saved,
        message=f"Successfully indexed {chunks_saved} chunks from '{file.filename}'.",
    )
