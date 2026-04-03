import psycopg2
from app.core.config import settings

def get_db_connection():
    """
    Returns a new PostgreSQL connection to Supabase via psycopg2.
    It uses the DATABASE_URL from the .env configuration.
    
    Make sure to close the connection and cursor after your queries:
    conn = get_db_connection()
    cursor = conn.cursor()
    # do things...
    cursor.close()
    conn.close()
    """
    try:
        connection = psycopg2.connect(settings.DATABASE_URL)
        return connection
    except Exception as e:
        print(f"Error connecting to Supabase direct PostgreSQL: {e}")
        raise
