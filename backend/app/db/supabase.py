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


def insert_document(conn, user_id: str, filename: str, file_type: str) -> uuid.UUID:
    """
    Inserts a row into the 'documents' table and returns the new UUID.

    Args:
        conn:      An open psycopg2 connection.
        user_id:   The UUID of the user uploading the document.
        filename:  Original filename of the uploaded file.
        file_type: File type string, e.g. 'pdf', 'docx', 'xlsx', 'image'.

    Returns:
        The UUID assigned to the new document row.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (user_id, filename, file_type)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (user_id, filename, file_type),
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

    if chunks and chunks[0].get("embedding"):
        print(f"DEBUG: insert_chunks received vectors of dimension {len(chunks[0]['embedding'])}")

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


def find_document_by_filename(conn, user_id: str, filename: str) -> dict | None:
    """
    Looks up a document by its filename and user_id.

    Returns:
        A dict with 'id', 'filename', 'file_type', 'created_at' and 'chunk_count'
        if found, else None.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.id, d.filename, d.file_type, d.created_at,
                   COUNT(c.id) AS chunk_count
            FROM documents d
            LEFT JOIN document_chunks c ON c.document_id = d.id
            WHERE d.filename = %s AND d.user_id = %s
            GROUP BY d.id
            ORDER BY d.created_at DESC
            LIMIT 1;
            """,
            (filename, user_id),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "filename": row[1],
        "file_type": row[2],
        "created_at": row[3],
        "chunk_count": row[4],
    }


def get_user_documents(conn, user_id: str) -> list[dict]:
    """
    Fetches all documents belonging to the user.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.id, d.filename, d.file_type, d.created_at, COUNT(c.id)
            FROM documents d
            LEFT JOIN document_chunks c ON c.document_id = d.id
            WHERE d.user_id = %s
            GROUP BY d.id
            ORDER BY d.created_at DESC;
            """,
            (user_id,)
        )
        rows = cur.fetchall()
        
    return [
        {
            "id": row[0],
            "filename": row[1],
            "file_type": row[2],
            "created_at": row[3],
            "chunk_count": row[4]
        } for row in rows
    ]


def delete_document(conn, document_id: uuid.UUID, user_id: str) -> bool:
    """
    Deletes a document row (and all its chunks via ON DELETE CASCADE).

    Returns:
        True if a row was deleted, False otherwise.
    """
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM documents WHERE id = %s AND user_id = %s;",
            (str(document_id), str(user_id)),
        )
        return cur.rowcount > 0


def search_keyword(conn, keyword: str, user_id: str, limit: int = 5) -> list[dict[str, Any]]:
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
            WHERE c.content ILIKE %s AND d.user_id = %s
            LIMIT %s;
            """,
            (f"%{keyword}%", user_id, limit)
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


def search_semantic(conn, embedding: list[float], user_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Searches the database semantically using the provided embedding vector and the HNSW index.
    """
    print(f"DEBUG: search_semantic received vector of dimension {len(embedding)}")
    with conn.cursor() as cur:
        # We use <=> which calculates cosine distance for pgvector
        cur.execute(
            """
            SELECT d.filename, d.file_type, c.content, c.location_metadata
            FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.user_id = %s
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s;
            """,
            (user_id, str(embedding), limit)
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


def get_recent_user_chunks(conn, user_id: str, limit: int = 15) -> list[dict[str, Any]]:
    """
    Fetches the most recently uploaded document chunks for a specific user to generate insights.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.filename, c.content 
            FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.user_id = %s
            ORDER BY d.created_at DESC, c.id ASC
            LIMIT %s;
            """,
            (user_id, limit)
        )
        rows = cur.fetchall()
        
    return [
        {"filename": row[0], "content": row[1]}
        for row in rows
    ]


def get_chunks_from_recent_docs(conn, user_id: str, doc_limit: int = 5, chunks_per_doc: int = 4) -> list[dict[str, Any]]:
    """
    Fetches chunks from the most recently interacted/uploaded documents.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH recent_docs AS (
                SELECT id, filename 
                FROM documents 
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            )
            SELECT d.filename, c.content
            FROM recent_docs d
            JOIN LATERAL (
                SELECT content
                FROM document_chunks
                WHERE document_id = d.id
                LIMIT %s
            ) c ON true;
            """,
            (user_id, doc_limit, chunks_per_doc)
        )
        rows = cur.fetchall()
        
    return [
        {"filename": row[0], "content": row[1]}
        for row in rows
    ]


def get_cached_insights(conn, user_id: str) -> dict | None:
    """
    Fetches the cached insights for a user from the database.
    Returns a dict with 'insights', 'suggestions', and 'updated_at', or None if not found.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT insights_data, suggestions_data, updated_at
            FROM user_insights
            WHERE user_id = %s;
            """,
            (user_id,)
        )
        row = cur.fetchone()
        
    if row is None:
        return None
        
    return {
        "insights": row[0],
        "suggestions": row[1],
        "updated_at": row[2]
    }


def upsert_cached_insights(conn, user_id: str, insights_data: list, suggestions_data: list):
    """
    Inserts or updates the cached insights for a user.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_insights (user_id, insights_data, suggestions_data, updated_at)
            VALUES (%s, %s::jsonb, %s::jsonb, timezone('utc'::text, now()))
            ON CONFLICT (user_id) DO UPDATE 
            SET insights_data = EXCLUDED.insights_data,
                suggestions_data = EXCLUDED.suggestions_data,
                updated_at = EXCLUDED.updated_at;
            """,
            (user_id, json.dumps(insights_data), json.dumps(suggestions_data))
        )


def upsert_chat_thread(conn, user_id: str, thread_id: str, title: str, associated_filename: str | None = None):
    """
    Inserts a new chat thread or updates the title and timestamp of an existing one.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chat_threads (user_id, thread_id, title, associated_filename, updated_at)
            VALUES (%s, %s, %s, %s, timezone('utc'::text, now()))
            ON CONFLICT (thread_id) DO UPDATE 
            SET title = COALESCE(chat_threads.title, EXCLUDED.title),
                updated_at = EXCLUDED.updated_at;
            """,
            (user_id, thread_id, title, associated_filename)
        )


def update_chat_thread_filenames(conn, thread_id: str, filenames: str):
    """
    Updates the associated_filename field for a given thread with a comma-separated list of filenames.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chat_threads 
            SET associated_filename = %s
            WHERE thread_id = %s;
            """,
            (filenames, thread_id)
        )


def get_user_chat_threads(conn, user_id: str) -> list[dict]:
    """
    Fetches all chat threads belonging to the user, ordered by most recently updated.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT thread_id, title, associated_filename, updated_at
            FROM chat_threads
            WHERE user_id = %s
            ORDER BY updated_at DESC;
            """,
            (user_id,)
        )
        rows = cur.fetchall()
        
    return [
        {
            "thread_id": row[0],
            "title": row[1],
            "associated_filename": row[2],
            "updated_at": row[3]
        } for row in rows
    ]


def delete_chat_thread(conn, user_id: str, thread_id: str) -> bool:
    """
    Deletes a specific chat thread.
    """
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM chat_threads WHERE user_id = %s AND thread_id = %s;",
            (user_id, thread_id)
        )
        return cur.rowcount > 0


def delete_all_chat_threads(conn, user_id: str) -> int:
    """
    Deletes all chat threads for a user.
    """
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM chat_threads WHERE user_id = %s;",
            (user_id,)
        )
        return cur.rowcount

