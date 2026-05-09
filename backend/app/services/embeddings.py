from openai import OpenAI
from app.core.config import settings

# Maximum number of texts sent to the embedding API in a single request.
_BATCH_SIZE = 256

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embedding vectors for a list of texts in batches using the OpenAI SDK.

    Args:
        texts: List of strings to embed. Each string is one document chunk.

    Returns:
        A list of float vectors in the same order as the input texts.
    """
    if not settings.EMBEDDING_MODEL_URL or not settings.EMBEDDING_MODEL_API_KEY or not settings.EMBEDDING_MODEL_NAME:
        raise ValueError(
            "Embedding model is not fully configured. "
            "Set EMBEDDING_MODEL_URL, EMBEDDING_MODEL_NAME, and EMBEDDING_MODEL_API_KEY in your .env file."
        )

    client = OpenAI(
        base_url=settings.EMBEDDING_MODEL_URL,
        api_key=settings.EMBEDDING_MODEL_API_KEY
    )

    all_embeddings: list[list[float]] = []

    # Process in batches to respect API payload limits
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]

        response = client.embeddings.create(
            input=batch,
            model=settings.EMBEDDING_MODEL_NAME,
            dimensions=1536  # Takes advantage of Matryoshka Representation Learning to output exactly 1536 dims
        )

        # The OpenAI SDK returns data sorted by index
        data = sorted(response.data, key=lambda x: x.index)
        batch_embeddings = [item.embedding for item in data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings