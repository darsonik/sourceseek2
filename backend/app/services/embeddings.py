import requests
from app.core.config import settings

def get_embedding(text: str) -> list:
    """
    Get the embedding vector for a given text using the Fireworks API.
    
    Args:
        text (str): The input text to be embedded.

    Returns:
        list: The embedding vector for the input text.
    """
    url = settings.EMBEDDING_MODEL_URL

    headers = {
        "Authorization": f"Bearer {settings.EMBEDDING_MODEL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": text,
        "model": settings.EMBEDDING_MODEL_URL,
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()["data"][0]["embedding"]