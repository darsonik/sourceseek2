-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS vector;    -- Semantic / AI Search
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- Fuzzy matching, typo-tolerance, and substrings
CREATE EXTENSION IF NOT EXISTS unaccent;  -- Accent-insensitive search (café = cafe)

-- The unaccent function is 'STABLE' by default in Postgres. 
-- To use it in automatic generated columns or indexes, we must wrap it in an IMMUTABLE function.
CREATE OR REPLACE FUNCTION immutable_unaccent(text)
  RETURNS text AS
$func$
SELECT public.unaccent('public.unaccent', $1)
$func$  LANGUAGE sql IMMUTABLE;

-- 2. Create the 'users' table to handle authentication
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Create the main 'documents' table to track files uploaded
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  file_type TEXT NOT NULL,          -- e.g., 'pdf', 'docx', 'xlsx'
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Create the 'document_chunks' table to store parsed text pieces
CREATE TABLE document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  content TEXT NOT NULL,            -- The extracted chunk of text
  location_metadata JSONB NOT NULL, -- Holds the exact precision data, e.g., {"page": 5, "line": 12, "cell": null}
  embedding vector(1536)            
);

-- 4. Create an HNSW index for lightning-fast semantic vector search
CREATE INDEX document_chunks_embedding_idx 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops);

-- 5. Native FTS + Unaccent (for linguistic token search)
-- This combines FTS with unaccent so searches ignore special characters and accents
ALTER TABLE document_chunks 
ADD COLUMN fts tsvector GENERATED ALWAYS AS (to_tsvector('english', immutable_unaccent(content))) STORED;

CREATE INDEX document_chunks_fts_idx 
ON document_chunks 
USING GIN (fts);

-- 6. Trigram Index (for fuzzy substring / wildcard matching like '%ID1234%')
-- This gives you blazing fast ILIKE queries that strict FTS might miss
CREATE INDEX document_chunks_trgm_idx 
ON document_chunks 
USING GIN (immutable_unaccent(content) gin_trgm_ops);

-- 7. User Insights cache for the homepage dashboard
CREATE TABLE user_insights (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  insights_data JSONB NOT NULL,
  suggestions_data JSONB NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 8. Chat Threads for keeping history of stateful search sessions
CREATE TABLE chat_threads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  thread_id TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  associated_filename TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);
