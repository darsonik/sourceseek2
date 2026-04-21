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
        cur.executemany(
            """
            INSERT INTO document_chunks (document_id, content, location_metadata, embedding)
            VALUES (%s, %s, %s::jsonb, %s::vector);
            """,
            [
                (
                    str(document_id),
                    chunk["content"],
                    json.dumps(chunk["location_metadata"]),
                    str(chunk.get("embedding")) if chunk.get("embedding") else None,
                )
                for chunk in chunks
            ],
        )
    return len(chunks)


def search_keyword(conn, keyword: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Searches the database for the exact keyword using the FTS and Trigram indexes.
    """
    with conn.cursor() as cur:
        # We will use ILIKE '%keyword%' to leverage the pg_trgm index
        cur.execute(
            """
            SELECT d.filename, d.file_type, c.content, c.location_metadata
            FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.content ILIKE %s
            LIMIT %s;
            """,
            (f"%{keyword}%", limit)
        )
        rows = cur.fetchall()
    
    return [
        {
            "filename": row[0],
            "file_type": row[1],
            "content": row[2],
            "location_metadata": row[3]
        }
        for row in rows
    ]


def search_semantic(conn, embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
    """
    Searches the database semantically using the provided embedding vector and the HNSW index.
    """
    with conn.cursor() as cur:
        # We use <=> which calculates cosine distance for pgvector
        cur.execute(
            """
            SELECT d.filename, d.file_type, c.content, c.location_metadata
            FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s;
            """,
            (str(embedding), limit)
        )
        rows = cur.fetchall()
        
    return [
        {
            "filename": row[0],
            "file_type": row[1],
            "content": row[2],
            "location_metadata": row[3]
        }
        for row in rows
    ]
