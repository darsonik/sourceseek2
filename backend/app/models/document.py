from pydantic import BaseModel
from typing import List
import uuid


class UploadResponse(BaseModel):
    """
    Returned to the client after a successful document upload and parse.
    """
    document_id: uuid.UUID
    filename: str
    file_type: str
    chunks_saved: int
    message: str


class ChunkMetadata(BaseModel):
    """
    Represents the location metadata attached to a single parsed chunk.
    Used internally — not returned directly to the API client.
    """
    page: int | None = None
    line: int | None = None
    paragraph_index: int | None = None
    section_heading: str | None = None
    style: str | None = None
    sheet: str | None = None
    row: int | None = None
    image_name: str | None = None
    image_format: str | None = None
