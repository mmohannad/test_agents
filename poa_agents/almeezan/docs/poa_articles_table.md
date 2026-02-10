# POA Articles Table Documentation

## Overview

The `poa_articles` table stores Power of Attorney (POA) related law articles from Qatar's Al Meezan legal portal. It contains 2,321 articles from 8 different Qatari laws, with bilingual content (Arabic/English) and vector embeddings for semantic search.

**Supabase Project:** `zvvwpbrzxbrkkhugnfkt`
**Table:** `poa_articles`

---

## Schema

```sql
CREATE TABLE poa_articles (
    id              BIGSERIAL PRIMARY KEY,
    idx             INTEGER,
    article_number  INTEGER NOT NULL,
    law_id          INTEGER NOT NULL,
    hierarchy_path  JSONB NOT NULL,
    citation        JSONB NOT NULL,
    text_arabic     TEXT NOT NULL,
    text_english    TEXT,
    embedding       VECTOR(1536),
    arabic_embedding VECTOR(1536),
    effective_date  DATE,
    is_active       BOOLEAN DEFAULT TRUE,
    updated         DATE,
    added           DATE,

    UNIQUE(law_id, article_number, idx)
);
```

---

## Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `id` | BIGSERIAL | Auto-generated primary key |
| `idx` | INTEGER | Sequential index within the dataset (0-based) |
| `article_number` | INTEGER | Article number within the law (e.g., 1, 2, 45) |
| `law_id` | INTEGER | Al Meezan Law ID (see Laws table below) |
| `hierarchy_path` | JSONB | Structural hierarchy (book, chapter, section, etc.) |
| `citation` | JSONB | Full citation info for referencing the article |
| `text_arabic` | TEXT | Original Arabic article text |
| `text_english` | TEXT | English translation (GPT-4o-mini) |
| `embedding` | VECTOR(1536) | English text embedding (text-embedding-3-small) |
| `arabic_embedding` | VECTOR(1536) | Arabic text embedding (text-embedding-3-small) |
| `effective_date` | DATE | Date the article became effective |
| `is_active` | BOOLEAN | Whether the law is currently in force |
| `updated` | DATE | Last update date |
| `added` | DATE | Date added to database |

---

## Laws Included

| law_id | Law Name (English) | Law Name (Arabic) | Articles |
|--------|-------------------|-------------------|----------|
| 9176 | Notarization Law | قانون التوثيق | ~20 |
| 2559 | Civil Code | القانون المدني | ~600 |
| 3993 | Traffic Law | قانون المرور | ~100 |
| 9564 | Real Estate Registration Law | قانون التسجيل العقاري | ~80 |
| 2492 | Civil & Commercial Procedures Law | قانون المرافعات المدنية والتجارية | ~400 |
| 2563 | Legal Practice Law | قانون المحاماة | ~80 |
| 6656 | Commercial Companies Law | قانون الشركات التجارية | ~350 |
| 2572 | Commercial Code | قانون التجارة | ~700 |

---

## JSONB Field Structures

### hierarchy_path

Represents the structural position of the article within the law:

```json
{
  "levels": [
    {
      "type": "book",
      "title_ar": "الكتاب الأول: الالتزامات بوجه عام",
      "title_en": "Book One: Obligations in General"
    },
    {
      "type": "part",
      "title_ar": "الباب الأول: مصادر الالتزام",
      "title_en": "Part One: Sources of Obligation"
    },
    {
      "type": "chapter",
      "title_ar": "الفصل الأول: العقد",
      "title_en": "Chapter One: Contract"
    },
    {
      "type": "section",
      "title_ar": "الفرع الأول: أركان العقد",
      "title_en": "Section One: Elements of Contract"
    }
  ]
}
```

**Hierarchy Level Types:**
- `book` (الكتاب) - Highest level division
- `part` (الباب) - Major part/title
- `chapter` (الفصل) - Chapter
- `section` (الفرع/القسم) - Section/branch
- `subsection` (المبحث) - Subsection

### citation

Full citation information for referencing:

```json
{
  "law_id": 2559,
  "law_number": 22,
  "law_year": 2004,
  "law_name_ar": "القانون المدني",
  "law_name_en": "Civil Code",
  "article_url": "https://www.almeezan.qa/LawArticles.aspx?...",
  "formatted_ar": "المادة 45 من القانون المدني رقم 22 لسنة 2004",
  "formatted_en": "Article 45 of Civil Code No. 22 of 2004"
}
```

---

## Indexes

```sql
-- Standard indexes
CREATE INDEX idx_poa_articles_law_id ON poa_articles(law_id);
CREATE INDEX idx_poa_articles_article_number ON poa_articles(article_number);
CREATE INDEX idx_poa_articles_is_active ON poa_articles(is_active);

-- JSONB indexes for hierarchy/citation queries
CREATE INDEX idx_poa_articles_hierarchy ON poa_articles USING GIN(hierarchy_path);
CREATE INDEX idx_poa_articles_citation ON poa_articles USING GIN(citation);

-- Vector indexes for similarity search (HNSW)
CREATE INDEX idx_poa_articles_embedding ON poa_articles
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_poa_articles_arabic_embedding ON poa_articles
    USING hnsw (arabic_embedding vector_cosine_ops);
```

---

## Example Queries

### Basic Queries

```sql
-- Get all articles from Civil Code
SELECT article_number, text_arabic, text_english
FROM poa_articles
WHERE law_id = 2559
ORDER BY article_number;

-- Get articles in a specific chapter
SELECT * FROM poa_articles
WHERE hierarchy_path @> '{"levels": [{"type": "chapter", "title_en": "Chapter One: Contract"}]}';

-- Count articles per law
SELECT
    citation->>'law_name_en' as law_name,
    COUNT(*) as article_count
FROM poa_articles
GROUP BY citation->>'law_name_en'
ORDER BY article_count DESC;
```

### Semantic Search (Vector Similarity)

```sql
-- Search English content (requires embedding of query text)
SELECT
    article_number,
    citation->>'formatted_en' as citation,
    text_english,
    1 - (embedding <=> $query_embedding) as similarity
FROM poa_articles
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $query_embedding
LIMIT 10;

-- Search Arabic content
SELECT
    article_number,
    citation->>'formatted_ar' as citation,
    text_arabic,
    1 - (arabic_embedding <=> $query_embedding) as similarity
FROM poa_articles
WHERE arabic_embedding IS NOT NULL
ORDER BY arabic_embedding <=> $query_embedding
LIMIT 10;
```

### Supabase RPC Function for Search

```sql
CREATE OR REPLACE FUNCTION search_poa_articles(
    query_embedding vector(1536),
    match_count int DEFAULT 10,
    language text DEFAULT 'en'
)
RETURNS TABLE (
    id bigint,
    article_number int,
    law_name text,
    citation_formatted text,
    content text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF language = 'ar' THEN
        RETURN QUERY
        SELECT
            p.id,
            p.article_number,
            p.citation->>'law_name_ar',
            p.citation->>'formatted_ar',
            p.text_arabic,
            1 - (p.arabic_embedding <=> query_embedding)
        FROM poa_articles p
        WHERE p.arabic_embedding IS NOT NULL
        ORDER BY p.arabic_embedding <=> query_embedding
        LIMIT match_count;
    ELSE
        RETURN QUERY
        SELECT
            p.id,
            p.article_number,
            p.citation->>'law_name_en',
            p.citation->>'formatted_en',
            p.text_english,
            1 - (p.embedding <=> query_embedding)
        FROM poa_articles p
        WHERE p.embedding IS NOT NULL
        ORDER BY p.embedding <=> query_embedding
        LIMIT match_count;
    END IF;
END;
$$;
```

---

## Data Pipeline

```
Al Meezan Portal
       │
       ▼
fetch_with_hierarchy.py    ─── Fetches articles with hierarchy from breadcrumbs
       │
       ▼
json_to_csv_v2.py          ─── Converts JSON to CSV format
       │
       ▼
generate_translations_embeddings.py  ─── Translates + generates embeddings
       │
       ▼
upload_to_supabase.py      ─── Batch uploads to Supabase
       │
       ▼
   poa_articles table
```

---

## Embedding Model

- **Model:** `text-embedding-3-small` (OpenAI)
- **Dimensions:** 1536
- **Used for:** Both English and Arabic text
- **Index type:** HNSW (Hierarchical Navigable Small World)
- **Distance metric:** Cosine similarity

---

## Notes

1. **Unique Constraint:** `(law_id, article_number, idx)` - Some laws have repeated article numbers in different sections, so `idx` ensures uniqueness.

2. **Empty Hierarchy:** Some simple laws (like Notarization Law) have flat structure with no chapters/sections, resulting in empty `levels` array.

3. **Translation Quality:** English translations are generated by GPT-4o-mini. For legal precision, always refer to the original Arabic text.

4. **Active Status:** `is_active` reflects whether the law was marked as "قيد التطبيق" (in force) at fetch time.
