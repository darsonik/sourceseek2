import requests
from app.core.config import settings

# Maximum number of texts sent to the embedding API in a single request.
# Most providers (OpenAI, Fireworks) support up to 2048 inputs per call,
# but keeping this lower avoids payload size issues.
_BATCH_SIZE = 256





def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embedding vectors for a list of texts in batches.

    Internally calls the configured embedding endpoint (any OpenAI-compatible
    API, including Fireworks) using the EMBEDDING_MODEL_URL and
    EMBEDDING_MODEL_API_KEY from settings.

    Args:
        texts: List of strings to embed. Each string is one document chunk.

    Returns:
        A list of float vectors in the same order as the input texts.

    Raises:
        ValueError: If the API credentials are not configured.
        requests.HTTPError: If the embedding API returns a non-2xx status.
    """
    if not settings.EMBEDDING_MODEL_URL or not settings.EMBEDDING_MODEL_API_KEY:
        raise ValueError(
            "Embedding model is not configured. "
            "Set EMBEDDING_MODEL_URL and EMBEDDING_MODEL_API_KEY in your .env file."
        )

    # Note: EMBEDDING_MODEL_URL should be the full endpoint URL,
    # e.g. https://api.fireworks.ai/inference/v1/embeddings
    # The model name is a separate setting.
    headers = {
        "Authorization": f"Bearer {settings.EMBEDDING_MODEL_API_KEY}",
        "Content-Type": "application/json",
    }

    all_embeddings: list[list[float]] = []

    # Process in batches to respect API payload limits
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]

        payload = {
            "input": batch,
            "model": settings.EMBEDDING_MODEL_NAME,
        }

        response = requests.post(settings.EMBEDDING_MODEL_URL, json=payload, headers=headers)
        response.raise_for_status()  # raises HTTPError for 4xx/5xx responses

        # The OpenAI-compatible response format returns data sorted by index
        data = sorted(response.json()["data"], key=lambda x: x["index"])
        batch_embeddings = [item["embedding"] for item in data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings