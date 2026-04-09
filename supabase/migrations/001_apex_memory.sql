-- APEX Memory Vector Store — Supabase pgvector
-- Case 1FDV-23-0001009 | GlacierEQ

CREATE EXTENSION IF NOT EXISTS vector;

-- Core memory table
CREATE TABLE IF NOT EXISTS apex_memory (
  id          bigserial PRIMARY KEY,
  content     text NOT NULL,
  metadata    jsonb DEFAULT '{}',
  embedding   vector(1536),
  created_at  timestamptz DEFAULT now()
);

-- Legal documents table
CREATE TABLE IF NOT EXISTS legal_documents (
  id          bigserial PRIMARY KEY,
  doc_type    text NOT NULL, -- motion, exhibit, order, declaration
  title       text NOT NULL,
  content     text NOT NULL,
  case_id     text DEFAULT '1FDV-23-0001009',
  filed_at    timestamptz,
  metadata    jsonb DEFAULT '{}',
  embedding   vector(1536),
  created_at  timestamptz DEFAULT now()
);

-- Case evidence table
CREATE TABLE IF NOT EXISTS case_evidence (
  id            bigserial PRIMARY KEY,
  evidence_type text NOT NULL, -- audio, document, screenshot, declaration
  title         text NOT NULL,
  description   text,
  file_path     text,
  hash_sha256   text, -- forensic integrity
  case_id       text DEFAULT '1FDV-23-0001009',
  collected_at  timestamptz DEFAULT now(),
  metadata      jsonb DEFAULT '{}',
  embedding     vector(1536)
);

-- Agent execution log
CREATE TABLE IF NOT EXISTS agent_logs (
  id          bigserial PRIMARY KEY,
  agent_name  text NOT NULL,
  task        text NOT NULL,
  output      text,
  duration_ms int,
  success     boolean DEFAULT true,
  metadata    jsonb DEFAULT '{}',
  created_at  timestamptz DEFAULT now()
);

-- Similarity search function
CREATE OR REPLACE FUNCTION match_apex_memory(
  query_embedding vector(1536),
  match_count     int DEFAULT 5,
  filter          jsonb DEFAULT '{}'
)
RETURNS TABLE (
  id          bigint,
  content     text,
  metadata    jsonb,
  similarity  float
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    am.id,
    am.content,
    am.metadata,
    1 - (am.embedding <=> query_embedding) AS similarity
  FROM apex_memory am
  WHERE am.metadata @> filter
  ORDER BY am.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Legal document search
CREATE OR REPLACE FUNCTION match_legal_documents(
  query_embedding vector(1536),
  match_count     int DEFAULT 5,
  doc_type_filter text DEFAULT NULL
)
RETURNS TABLE (
  id          bigint,
  title       text,
  doc_type    text,
  content     text,
  similarity  float
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    ld.id,
    ld.title,
    ld.doc_type,
    ld.content,
    1 - (ld.embedding <=> query_embedding) AS similarity
  FROM legal_documents ld
  WHERE (doc_type_filter IS NULL OR ld.doc_type = doc_type_filter)
  ORDER BY ld.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS apex_memory_embedding_idx
  ON apex_memory USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS legal_docs_embedding_idx
  ON legal_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS case_evidence_embedding_idx
  ON case_evidence USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS apex_memory_case_idx ON apex_memory ((metadata->>'caseId'));
CREATE INDEX IF NOT EXISTS legal_docs_case_idx ON legal_documents (case_id);
CREATE INDEX IF NOT EXISTS evidence_case_idx ON case_evidence (case_id);

COMMIT;
