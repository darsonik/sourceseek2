import sys
import os

# Add backend to sys.path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.embeddings import get_embeddings
from app.core.config import settings

def main():
    print(f"Model: {settings.EMBEDDING_MODEL_NAME}")
    res = get_embeddings(["This is a test"])
    print(f"Dimension size returned: {len(res[0])}")

if __name__ == "__main__":
    main()
