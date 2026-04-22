import sys
import os
import psycopg2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.config import settings

def main():
    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    
    # Test 1536 vector
    try:
        cur.execute("SELECT embedding <=> %s::vector FROM document_chunks LIMIT 1;", ('[' + '0,'*1535 + '0]',))
        print("1536 query succeeded!")
    except Exception as e:
        print(f"1536 query failed: {e}")
        
    conn.rollback()

    # Test 768 vector
    try:
        cur.execute("SELECT embedding <=> %s::vector FROM document_chunks LIMIT 1;", ('[' + '0,'*767 + '0]',))
        print("768 query succeeded!")
    except Exception as e:
        print(f"768 query failed: {e}")

    conn.close()

if __name__ == "__main__":
    main()
