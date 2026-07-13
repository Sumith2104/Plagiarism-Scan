-- === PlagiaScan: corrected & improved schema ===

-- Enum types (create before tables)
CREATE TYPE user_role AS ENUM ('admin', 'user');
CREATE TYPE doc_status AS ENUM ('pending', 'processing', 'indexed', 'failed');
CREATE TYPE scan_status AS ENUM ('queued', 'scanning', 'completed', 'failed');

-- Helper: automatic updated_at maintenance
CREATE OR REPLACE FUNCTION trg_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role user_role NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION trg_set_timestamp();

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_hash VARCHAR(64), -- SHA256 hex (64 chars) for deduplication
    content_type VARCHAR(100),
    file_size INTEGER,
    status doc_status NOT NULL DEFAULT 'pending',
    extracted_text TEXT, -- Store extracted text (or link to file)
    meta_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_documents_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW
EXECUTE FUNCTION trg_set_timestamp();

-- Document chunks (for embedding / vector indexing)
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    vector_id VARCHAR(128), -- Reference to external vector DB (Qdrant point id etc.)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_document_chunks_updated_at
BEFORE UPDATE ON document_chunks
FOR EACH ROW
EXECUTE FUNCTION trg_set_timestamp();

-- Scans table (each plagiarism scan run)
CREATE TABLE IF NOT EXISTS scans (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    initiated_by INTEGER REFERENCES users(id),
    status scan_status NOT NULL DEFAULT 'queued',
    overall_score DOUBLE PRECISION DEFAULT 0.0,
    report_data JSONB NOT NULL DEFAULT '{}'::jsonb, -- Detailed report structure
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_scans_updated_at
BEFORE UPDATE ON scans
FOR EACH ROW
EXECUTE FUNCTION trg_set_timestamp();

-- Scan matches (individual matches found during a scan)
CREATE TABLE IF NOT EXISTS scan_matches (
    id SERIAL PRIMARY KEY,
    scan_id INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    source_document_id INTEGER REFERENCES documents(id), -- internal match (nullable if external)
    external_source_url VARCHAR(1024), -- Web match (nullable if internal)
    similarity_score DOUBLE PRECISION NOT NULL,
    matched_fragments JSONB NOT NULL DEFAULT '[]'::jsonb, -- array of objects: [{ "start": .., "end": .., "text": ".." }]
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Indexes and useful access patterns
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_scans_document ON scans(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_scan_matches_scan ON scan_matches(scan_id);

-- Optional: GIN indexes for JSONB columns (fast querying by keys/values)
CREATE INDEX IF NOT EXISTS idx_documents_meta_data_gin ON documents USING GIN (meta_data);
CREATE INDEX IF NOT EXISTS idx_scans_report_data_gin ON scans USING GIN (report_data);
CREATE INDEX IF NOT EXISTS idx_scan_matches_fragments_gin ON scan_matches USING GIN (matched_fragments);

-- Optional: If you want to enforce file_hash uniqueness across uploads, uncomment:
-- ALTER TABLE documents ADD CONSTRAINT documents_file_hash_unique UNIQUE (file_hash);

-- === End of schema ===
