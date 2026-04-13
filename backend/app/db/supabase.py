import json
import uuid
from typing import Any

import psycopg2
from app.core.config import settings


def get_db_connection():
    """
    Returns a new raw psycopg2 PostgreSQL connection to Supabase.
    Always close the cursor and connection after use.
    """
    try:
        return psycopg2.connect(settings.DATABASE_URL)
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        raise


def insert_document(conn, filename: str, file_type: str) -> uuid.UUID:
    """
    Inserts a row into the 'documents' table and returns the new UUID.

    Args:
        conn:      An open psycopg2 connection.
        filename:  Original filename of the uploaded file.
        file_type: File type string, e.g. 'pdf', 'docx', 'xlsx', 'image'.

    Returns:
        The UUID assigned to the new document row.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (filename, file_type)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (filename, file_type),
        )
        row = cur.fetchone()
    return row[0]


def insert_chunks(conn, document_id: uuid.UUID, chunks: list[dict[str, Any]]) -> int:
    """
    Bulk-inserts a list of parsed chunk dicts into 'document_chunks'.
    Each dict must have 'content' (str) and 'location_metadata' (dict) keys.

    Args:
        conn:        An open psycopg2 connection.
        document_id: UUID of the parent document row.
        chunks:      List of {'content': str, 'location_metadata': dict}.

    Returns:
        Number of rows inserted.
    """
    if not chunks:
        return 0

    with conn.cursor() as cur:
        # executemany is simple and clear for moderate chunk counts.
        # For very large files (thousands of chunks) switch to execute_values.
        cur.executemany(
            """
            INSERT INTO document_chunks (document_id, content, location_metadata)
            VALUES (%s, %s, %s::jsonb);
            """,
            [
                (
                    str(document_id),
                    chunk["content"],
                    json.dumps(chunk["location_metadata"]),
                )
                for chunk in chunks
            ],
        )
    return len(chunks)
