import os
import sys

# Add backend directory to path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.db.supabase import get_db_connection

def reset_database():
    """
    Connects to the Supabase PostgreSQL database and deletes all uploaded
    documents and their chunks.
    """
    print("Connecting to the database...")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            print("Truncating 'documents' and 'document_chunks' tables...")
            # CASCADE will automatically delete associated document_chunks
            cur.execute("TRUNCATE TABLE documents CASCADE;")
            
            # If you also want to clear LangGraph chat history, uncomment these lines:
            print("Truncating LangGraph checkpoint tables...")
            cur.execute("TRUNCATE TABLE checkpoints CASCADE;")
            cur.execute("TRUNCATE TABLE checkpoint_blobs CASCADE;")
            cur.execute("TRUNCATE TABLE checkpoint_writes CASCADE;")
            
            conn.commit()
            print("✅ Database data deleted successfully.")
    except Exception as e:
        print(f"❌ Error deleting data: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    confirm = input("This will delete ALL uploaded documents. Are you sure? (y/n): ")
    if confirm.lower() == 'y':
        reset_database()
    else:
        print("Operation cancelled.")
