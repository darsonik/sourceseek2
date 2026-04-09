"""
Test script to verify the Supabase (PostgreSQL) connection is working.

Run this from the backend directory:
    uv run python tests/test_supabase.py

What it does:
  1. Connects to the database
  2. Inserts a test row into 'documents'
  3. Inserts a test row into 'document_chunks' (no embedding yet)
  4. Reads both rows back and prints them
  5. Cleans up by deleting the test rows
"""

import sys
import os

# Allow imports from the project root (app.core.config, app.db.supabase)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.supabase import get_db_connection


def run_test():
    print("Connecting to Supabase...")
    conn = get_db_connection()
    cursor = conn.cursor()
    print("Connected!\n")

    test_document_id = None

    try:
        # ------------------------------------------------------------------
        # 1. INSERT a test document
        # ------------------------------------------------------------------
        print("Inserting test document...")
        cursor.execute(
            """
            INSERT INTO documents (filename, file_type)
            VALUES (%s, %s)
            RETURNING id, filename, file_type, created_at;
            """,
            ("test_document.pdf", "pdf"),
        )
        doc_row = cursor.fetchone()
        test_document_id = doc_row[0]
        print(f"  Inserted document  -> id={doc_row[0]}  filename={doc_row[1]}  type={doc_row[2]}  created_at={doc_row[3]}\n")

        # ------------------------------------------------------------------
        # 2. INSERT a test chunk (no embedding yet -- column is nullable)
        # ------------------------------------------------------------------
        print("Inserting test document_chunk...")
        cursor.execute(
            """
            INSERT INTO document_chunks (document_id, content, location_metadata)
            VALUES (%s, %s, %s::jsonb)
            RETURNING id, content, location_metadata;
            """,
            (
                test_document_id,
                "This is a test chunk. Employee ID: ID1234. Department: Finance.",
                '{"page": 1, "line": 1, "bbox": {"x0": 72.0, "top": 100.0, "x1": 540.0, "bottom": 112.0}}',
            ),
        )
        chunk_row = cursor.fetchone()
        print(f"  Inserted chunk     -> id={chunk_row[0]}")
        print(f"  content            -> {chunk_row[1]}")
        print(f"  location_metadata  -> {chunk_row[2]}\n")

        conn.commit()

        # ------------------------------------------------------------------
        # 3. READ BACK -- verify both rows are in the database
        # ------------------------------------------------------------------
        print("Reading rows back from the database...")
        cursor.execute(
            """
            SELECT d.filename, d.file_type, c.content, c.location_metadata
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.id = %s;
            """,
            (test_document_id,),
        )
        results = cursor.fetchall()
        for r in results:
            print(f"  filename={r[0]}  type={r[1]}")
            print(f"  content={r[2]}")
            print(f"  location={r[3]}\n")

        print("All tests PASSED\n")

    except Exception as e:
        conn.rollback()
        print(f"\nTest FAILED: {e}")
        raise

    finally:
        # ------------------------------------------------------------------
        # 4. CLEAN UP -- delete test rows so they don't pollute the database
        # ------------------------------------------------------------------
        if test_document_id:
            print("Cleaning up test rows...")
            # Deleting the document will CASCADE-delete the chunk automatically
            cursor.execute("DELETE FROM documents WHERE id = %s;", (test_document_id,))
            conn.commit()
            print("Cleanup done.")
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_test()
