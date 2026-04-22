import sys
import os
import psycopg2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.config import settings

def main():
    conn = psycopg2.connect(settings.DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    cur.execute("TRUNCATE TABLE document_chunks CASCADE;")
    cur.execute("TRUNCATE TABLE documents CASCADE;")
    
    print("Successfully truncated tables.")
    conn.close()

if __name__ == "__main__":
    main()
