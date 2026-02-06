-- Supabase Migration: Create POA Articles Table
-- Run this in the SQL Editor panel

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Create articles table for POA laws
CREATE TABLE IF NOT EXISTS poa_articles (
    id BIGSERIAL PRIMARY KEY,
    idx INTEGER,
    article_number INTEGER NOT NULL,
    law_id INTEGER NOT NULL,

    -- Hierarchical structure (level, chapter, section)
    hierarchy_path JSONB NOT NULL,

    -- Citation info for downstream apps
    citation JSONB NOT NULL,

    -- Article content
    text_arabic TEXT NOT NULL,
    text_english TEXT,

    -- Embeddings (1536 dimensions for OpenAI, adjust if using different model)
    embedding VECTOR(1536),
    arabic_embedding VECTOR(1536),

    -- Metadata
    effective_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    updated DATE,
    added DATE,

    -- Unique constraint: one article per law
    UNIQUE(law_id, article_number)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_poa_articles_law_id ON poa_articles(law_id);
CREATE INDEX IF NOT EXISTS idx_poa_articles_article_number ON poa_articles(article_number);
CREATE INDEX IF NOT EXISTS idx_poa_articles_is_active ON poa_articles(is_active);
CREATE INDEX IF NOT EXISTS idx_poa_articles_hierarchy ON poa_articles USING GIN(hierarchy_path);
CREATE INDEX IF NOT EXISTS idx_poa_articles_citation ON poa_articles USING GIN(citation);

-- Create vector indexes for similarity search (using HNSW for better performance)
CREATE INDEX IF NOT EXISTS idx_poa_articles_embedding ON poa_articles
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_poa_articles_arabic_embedding ON poa_articles
    USING hnsw (arabic_embedding vector_cosine_ops);

-- Add comments for documentation
COMMENT ON TABLE poa_articles IS 'Power of Attorney related law articles from Al Meezan';
COMMENT ON COLUMN poa_articles.law_id IS 'Al Meezan Law ID (e.g., 2563 for Legal Practice Law)';
COMMENT ON COLUMN poa_articles.hierarchy_path IS 'JSON: {level, chapter: {ar, en}, section: {ar, en}}';
COMMENT ON COLUMN poa_articles.citation IS 'JSON: {law_id, law_number, law_year, law_name_ar/en, article_url, formatted_ar/en}';
COMMENT ON COLUMN poa_articles.embedding IS 'Vector embedding of English text (1536 dims)';
COMMENT ON COLUMN poa_articles.arabic_embedding IS 'Vector embedding of Arabic text (1536 dims)';

-- Enable Row Level Security (optional, uncomment if needed)
-- ALTER TABLE poa_articles ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Public read access" ON poa_articles FOR SELECT USING (true);
