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


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "SourceSeek API is running."}
