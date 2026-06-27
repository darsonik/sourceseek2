# SourceSeek Backend

A **hybrid document search API** built with FastAPI. Upload PDFs, Word documents, Excel spreadsheets, and images — then query them using natural language or exact keyword search powered by an LLM-driven agentic pipeline.

---

## Features

- **Multi-format document ingestion** — PDF, DOCX, XLSX, and images (JPEG, PNG, WEBP, GIF, TIFF)
- **Precision metadata extraction** — page & line numbers for PDFs, paragraph index for Word, cell references (e.g. `B4`) for Excel
- **Hybrid search** — keyword search for exact matches (IDs, codes) and semantic/vector search for conceptual queries
- **Stateful conversational search** — threaded, multi-turn chat powered by LangGraph with PostgreSQL checkpointing
- **AI-generated insights** — automatic key insights and suggested follow-up questions derived from recently uploaded documents, cached and refreshed every 30 minutes
- **Backblaze B2 file storage** — original files are stored in the cloud and can be downloaded at any time
- **JWT authentication** — user registration, login, and per-user data isolation

---

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI + Uvicorn |
| AI orchestration | LangGraph + LangChain |
| LLM / Embeddings | OpenAI-compatible API (configurable via env) |
| Database | PostgreSQL (via `psycopg3`) |
| File storage | Backblaze B2 (`b2sdk`) |
| Document parsing | `pdfplumber`, `python-docx`, `openpyxl`, Pillow |
| Auth | PyJWT + bcrypt |
| Config | Pydantic Settings |
| Package manager | `uv` |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point, CORS, router registration
│   ├── core/
│   │   ├── config.py        # Pydantic Settings — loads .env variables
│   │   └── security.py      # JWT creation/verification, password hashing
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py      # POST /auth/register, POST /auth/login
│   │       ├── documents.py # Upload, list, delete, and download documents
│   │       ├── search.py    # Stateful conversational search
│   │       ├── insights.py  # AI-generated insights and suggested questions
│   │       └── history.py   # Chat thread history
│   ├── agents/
│   │   ├── search_agent.py  # LangGraph agent graph with PostgreSQL checkpointing
│   │   └── tools.py         # keyword_search_tool, semantic_search_tool
│   ├── services/
│   │   ├── parser.py        # Document parsers (PDF, DOCX, XLSX, image)
│   │   ├── embeddings.py    # Text-to-vector embedding generation
│   │   └── b2_service.py    # Backblaze B2 upload/download/delete
│   ├── db/
│   │   └── supabase.py      # PostgreSQL queries (documents, chunks, threads, insights)
│   └── models/
│       └── document.py      # Pydantic request/response schemas
├── tests/                   # pytest test suite
├── migrate.py               # Database migration runner
├── reset_db.py              # Drops and recreates all tables (dev only)
├── .env.example             # Environment variable template
├── pyproject.toml           # Project metadata and dependencies (managed by uv)
└── ARCHITECTURE.md          # Detailed architecture reference
```

---

## Getting Started

### Prerequisites

- Python 3.14+
- [`uv`](https://github.com/astral-sh/uv) package manager
- A running PostgreSQL database
- A Backblaze B2 bucket (for file storage)
- An OpenAI-compatible API endpoint (for embeddings and the search agent)

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd backend

# Install all dependencies using uv
uv sync
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

```env
# --- Required ---
DATABASE_URL=postgresql://user:password@host:5432/dbname
SECRET_KEY=your-strong-random-secret-key

# --- AI Provider (required for search and insights) ---
VISION_MODEL_NAME=your-model-name          # e.g. gpt-4o
VISION_MODEL_URL=https://api.openai.com/v1 # or any compatible base URL
VISION_MODEL_API_KEY=your-api-key

EMBEDDING_MODEL_NAME=your-embedding-model  # e.g. text-embedding-3-small
EMBEDDING_MODEL_URL=https://api.openai.com/v1
EMBEDDING_MODEL_API_KEY=your-api-key

# --- Backblaze B2 (required for file storage) ---
BLACKBLAZE_APPLICATION_KEY_ID=your-key-id
BLACKBLAZE_APPLICATION_KEY=your-application-key
BLACKBLAZE_BUCKET_NAME=your-bucket-name
```

### 3. Run database migrations

```bash
uv run python migrate.py
```

> To fully reset the database in development, run `uv run python reset_db.py`.

### 4. Start the development server

```bash
uv run uvicorn app.main:app --reload --host localhost --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs (Swagger UI) are served at `http://localhost:8000/docs`.

---

## API Overview

All endpoints are prefixed with `/api/v1`. Protected endpoints require a `Bearer` token in the `Authorization` header.

### Auth

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register a new user, returns a JWT |
| `POST` | `/api/v1/auth/login` | Login and receive a JWT |

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents/upload` | Upload and index a document |
| `GET` | `/api/v1/documents` | List all documents for the authenticated user |
| `GET` | `/api/v1/documents/check?filename=...` | Check if a filename has already been indexed |
| `GET` | `/api/v1/documents/{id}/download?filename=...` | Download the original file from B2 |
| `DELETE` | `/api/v1/documents/{id}` | Delete a document and its indexed chunks |

**Supported upload formats:** PDF, DOCX, XLSX, JPEG, PNG, WEBP, GIF, TIFF

The `force_reprocess=true` query parameter on `/upload` will delete the old indexed data and re-process the file from scratch.

### Search

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/search` | Run a conversational search query |

Request body:
```json
{
  "query": "What were the Q3 revenue figures?",
  "thread_id": "my-thread-123",
  "associated_filename": "Q3_report.pdf"
}
```

The agent automatically chooses between **keyword search** and **semantic search** based on the query. Conversation history is persisted per `thread_id` using LangGraph's PostgreSQL checkpointer, enabling multi-turn follow-up questions.

### Insights

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/insights` | Get AI-generated insights and suggested questions |

Returns 2 key insights and 3 suggested questions derived from the user's most recently uploaded documents. Results are cached in the database and refreshed in the background at most every 30 minutes.

### History

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/history` | List chat threads for the authenticated user |
| `GET` | `/api/v1/history/{thread_id}` | Get messages for a specific thread |

---

## Application Flow

```
Frontend Request
      │
      ▼
 API Route (app/api/routes/)
      │  validates JWT, parses request body
      ▼
 Service / Agent (app/services/ or app/agents/)
      │  does the heavy lifting: parsing, embedding, LLM calls
      ▼
 Database Layer (app/db/)
      │  reads/writes chunks, documents, threads to PostgreSQL
      ▼
 Response returned to client
```

For search queries specifically:

```
POST /search
      │
      ▼
  LangGraph agent (search_agent.py)
      │  decides: keyword or semantic search?
      ▼
  Tool call (tools.py)
      │  queries PostgreSQL for matching chunks
      ▼
  LLM synthesizes answer
      │  with exact source citations (page, line, cell)
      ▼
  Streamed back as SearchResponse
```

---

## Running Tests

```bash
uv run pytest tests/
```

---

## Development Notes

- **CORS** is currently set to `allow_origins=["*"]`. Restrict this before deploying to production.
- The LangGraph checkpointer uses a lazy-initialized connection pool to avoid thread deadlocks on Windows during startup.
- Insights generation is triggered as a background task after every upload, delete, and search — but will only re-run if the cached results are older than 30 minutes.
- The `SECRET_KEY` environment variable is used to sign JWTs. Use a cryptographically strong random value in production (e.g. `openssl rand -hex 32`).
