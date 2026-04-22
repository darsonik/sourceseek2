import sys
import os
import psycopg2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.config import settings

def main():
    conn = psycopg2.connect(settings.DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    cur.execute("""
        SELECT pid, state, query 
        FROM pg_stat_activity 
        WHERE datname = current_database() 
        AND pid <> pg_backend_pid();
    """)
    rows = cur.fetchall()
    print(f"Active connections: {len(rows)}")
    for r in rows:
        print(r)
        
    print("\nTerminating other connections...")
    cur.execute("""
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE datname = current_database() 
        AND pid <> pg_backend_pid();
    """)
    print("Done.")

if __name__ == "__main__":
    main()
