import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import documents, search

app = FastAPI(
    title="SourceSeek API",
    description="Hybrid document search backend — upload files and query them with natural language or exact keywords.",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS — allow the frontend dev server to call this API
# Tighten origins before deploying to production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(documents.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")


from app.core.config import settings

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "SourceSeek API is running.", "model": settings.EMBEDDING_MODEL_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)