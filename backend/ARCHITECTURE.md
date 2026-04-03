# SourceSeek Backend: Architecture & File Reference

This document explains the purpose of each directory and file in the backend folder structure. You can reference this as you build out the application to ensure clean architecture and separation of concerns.

## Application Flow Overview
1. **API Endpoints** (`app/api/routes`) receive requests from the frontend.
2. The endpoints use **Pydantic Models** (`app/models`) to validate the incoming data.
3. The endpoints call **Services** (`app/services`) to do the heavy lifting (like parsing documents or generating embeddings).
4. The services use the **Database Layer** (`app/db`) to save or retrieve data from Supabase.
5. If the request is a search query, it gets routed to the **Agents** (`app/agents`) to handle natural language routing, database querying, and final generation.

---

## Directory & File Breakdown

### 1. The Core Application (`app/`)
This is the root package of your actual backend application footprint.

* **`app/main.py`**
  * **Purpose:** The entry point for your FastAPI server.
  * **Used for:** Initializing the `FastAPI()` app, setting up CORS middleware (so your frontend can talk to it), and including the routers from `app/api`.

* **`app/core/config.py`**
  * **Purpose:** Configuration management.
  * **Used for:** Defining a Pydantic `BaseSettings` class that loads variables from your `.env` file (like `SUPABASE_URL`, `OPENAI_API_KEY`). This ensures your app knows about environment variables in a type-safe way and will throw errors on startup if required keys are missing.

### 2. The API Layer (`app/api/`)
This layer is strictly for defining API endpoints. Keeping business logic out of here makes your app easier to maintain.

* **`app/api/routes/documents.py`**
  * **Purpose:** The endpoints for document operations.
  * **Used for:** Defining routes like `POST /upload` (to receive files) and `POST /search` (to receive user queries). These routes will immediately pass off the actual "work" to files inside `app/services/` or `app/agents/`.

### 3. The Services Layer (`app/services/`)
This layer holds the core business logic.

* **`app/services/parser.py`**
  * **Purpose:** Document ingestion and chunking.
  * **Used for:** Receiving an uploaded file, identifying its type, and using libraries like `pdfplumber`, `python-docx`, or `pandas` to read it. It breaks the text into logical chunks and attaches precision metadata (page number, exact line number, or excel cell number) to each chunk.

* **`app/services/embeddings.py`**
  * **Purpose:** Generating AI vectors.
  * **Used for:** Taking the parsed text chunks from `parser.py` and sending them to an embedding model (like OpenAI or HuggingFace) to generate the vector arrays required for semantic search.

### 4. The Database Layer (`app/db/`)
* **`app/db/supabase.py`**
  * **Purpose:** The database client provider.
  * **Used for:** Initializing the Supabase Python client using the credentials from `app/core/config.py`. It can expose a function like `get_db()` which endpoints or services can import to interact with Supabase tables.

### 5. The Models Layer (`app/models/`)
* **`app/models/document.py`**
  * **Purpose:** Defining data structures using Pydantic.
  * **Used for:** Creating schemas that represent exactly what data the frontend must send over, or what the backend will return.
  * **Examples:** `SearchRequest` (defines a user query), `ChunkMetadata` (defines the page/line structure), `UploadResponse` (returns success status).

### 6. The AI Agents Layer (`app/agents/`)
This directory contains the AI orchestration logic.

* **`app/agents/search_agent.py`**
  * **Purpose:** The brain of the search panel.
  * **Used for:** Receiving the user query from the API, analyzing it to decide if it's a keyword search ("ID1234") or semantic search ("which document..."). Based on the decision, it queries Supabase. Once Supabase returns the text chunks, the agent synthesizes the chunks into a conversational, human-readable response that includes the exact line/cell metadata.

### 7. Root-level Configuration
* **`requirements.txt`**: List of all Python dependencies. (Note: These have already been successfully installed via `uv add`!).
* **`.env.example`**: A template file. When another developer clones this repo, they will copy this to a new file named `.env` and fill in their actual API keys.
* **`pyproject.toml`**: The modern Python project configuration file created by `uv`, holding project metadata.
* **`tests/`**: The folder where you will write `pytest` files to ensure each part of the app works correctly before deploying to production.
