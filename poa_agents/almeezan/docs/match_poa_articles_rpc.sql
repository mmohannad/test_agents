-- RPC Function for semantic search on poa_articles table
-- Run this in Supabase SQL Editor to create the function

CREATE OR REPLACE FUNCTION match_poa_articles(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.3,
    match_count int DEFAULT 10,
    language text DEFAULT 'english'
)
RETURNS TABLE (
    id bigint,
    article_number int,
    law_id int,
    text_arabic text,
    text_english text,
    hierarchy_path jsonb,
    citation jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF language = 'arabic' THEN
        -- Use arabic_embedding for Arabic queries
        RETURN QUERY
        SELECT
            p.id,
            p.article_number,
            p.law_id,
            p.text_arabic,
            p.text_english,
            p.hierarchy_path,
            p.citation,
            (1 - (p.arabic_embedding <=> query_embedding))::float as similarity
        FROM poa_articles p
        WHERE p.arabic_embedding IS NOT NULL
          AND p.is_active = TRUE
          AND (1 - (p.arabic_embedding <=> query_embedding)) >= match_threshold
        ORDER BY p.arabic_embedding <=> query_embedding
        LIMIT match_count;
    ELSE
        -- Use embedding (English) for English queries
        RETURN QUERY
        SELECT
            p.id,
            p.article_number,
            p.law_id,
            p.text_arabic,
            p.text_english,
            p.hierarchy_path,
            p.citation,
            (1 - (p.embedding <=> query_embedding))::float as similarity
        FROM poa_articles p
        WHERE p.embedding IS NOT NULL
          AND p.is_active = TRUE
          AND (1 - (p.embedding <=> query_embedding)) >= match_threshold
        ORDER BY p.embedding <=> query_embedding
        LIMIT match_count;
    END IF;
END;
$$;

-- Grant execute permission to authenticated and anon users
GRANT EXECUTE ON FUNCTION match_poa_articles TO authenticated;
GRANT EXECUTE ON FUNCTION match_poa_articles TO anon;

-- Test the function (replace with actual embedding vector)
-- SELECT * FROM match_poa_articles(
--     '[0.1, 0.2, ...]'::vector(1536),
--     0.3,
--     10,
--     'arabic'
-- );
