from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig

from app.db.supabase import get_db_connection, search_keyword, search_semantic
from app.services.embeddings import get_embeddings

@tool
def keyword_search_tool(query: str, config: RunnableConfig) -> str:
    """
    Use this tool when the user asks for a specific exact string, ID, or name (e.g. 'ID1234' or 'John Smith').
    This performs a strict fuzzy text match across all documents and returns the relevant chunks.
    """
    try:
        user_id = config["configurable"].get("user_id")
        if not user_id:
            return "Error: user_id not provided in config."
            
        conn = get_db_connection()
        results = search_keyword(conn, query, user_id, limit=5)
        conn.close()
        
        if not results:
            return "No exact matches found."
            
        formatted_results = []
        for i, res in enumerate(results, 1):
            formatted_results.append(
                f"[Result {i}]\nFile: {res['filename']}\nLocation: {res['location_metadata']}\nContent: {res['content']}\n"
            )
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Error executing keyword search: {str(e)}"

@tool
def semantic_search_tool(query: str, config: RunnableConfig) -> str:
    """
    Use this tool when the user asks a natural language question or conceptual query (e.g. 'What is the refund policy?').
    This performs an AI-powered vector similarity search and returns the most relevant chunks.
    """
    try:
        user_id = config["configurable"].get("user_id")
        if not user_id:
            return "Error: user_id not provided in config."
            
        # Convert the string query to an embedding vector
        embedding = get_embeddings([query])[0]
        
        conn = get_db_connection()
        results = search_semantic(conn, embedding, user_id, limit=5)
        conn.close()
        
        if not results:
            return "No semantic matches found."
            
        formatted_results = []
        for i, res in enumerate(results, 1):
            formatted_results.append(
                f"[Result {i}]\nFile: {res['filename']}\nLocation: {res['location_metadata']}\nContent: {res['content']}\n"
            )
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Error executing semantic search: {str(e)}"
