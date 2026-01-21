#!/usr/bin/env python3
"""
Generate embeddings for TEST articles (90001-90006) only.
Uses OpenAI API (not Azure) following the law_parser approach.

Usage:
    python 003_generate_embeddings.py
"""
import os
import time
import logging
from openai import OpenAI
from supabase import create_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', "REDACTED_OPENAI_KEY")
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
EMBEDDING_DIMENSIONS = int(os.getenv('EMBEDDING_DIMENSIONS', '1536'))
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://zvvwpbrzxbrkkhugnfkt.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp2dndwYnJ6eGJya2todWduZmt0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgyNTY1OTIsImV4cCI6MjA4MzgzMjU5Mn0.kt8IKVzaq_jFOAVCFoHcWAdhMUH6_EB23UTumY9lvi0')

# Test article range - use 90001-90006 for test articles
TEST_ARTICLE_START = 1
TEST_ARTICLE_END = 6


def embed_text(client: OpenAI, text: str) -> list[float]:
    """Generate embedding for text using OpenAI."""
    if not text or not text.strip():
        logger.warning("Empty text provided, returning zero vector")
        return [0.0] * EMBEDDING_DIMENSIONS

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS
    )
    return response.data[0].embedding


def main():
    logger.info("=" * 60)
    logger.info("GENERATE EMBEDDINGS FOR TEST ARTICLES")
    logger.info("=" * 60)
    logger.info(f"OpenAI API Key: {'*' * 10}...{OPENAI_API_KEY[-4:]}")
    logger.info(f"Embedding Model: {EMBEDDING_MODEL}")
    logger.info(f"Embedding Dimensions: {EMBEDDING_DIMENSIONS}")
    logger.info(f"Supabase URL: {SUPABASE_URL}")
    logger.info(f"Article Range: {TEST_ARTICLE_START} - {TEST_ARTICLE_END}")
    logger.info("=" * 60)

    # Initialize clients
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Fetch test articles (90001-90006)
    logger.info(f"\nFetching test articles ({TEST_ARTICLE_START}-{TEST_ARTICLE_END})...")
    response = supabase.table("articles") \
        .select("*") \
        .gte("article_number", TEST_ARTICLE_START) \
        .lte("article_number", TEST_ARTICLE_END) \
        .execute()

    articles = response.data if response.data else []
    logger.info(f"Found {len(articles)} test articles")

    if not articles:
        logger.warning("No test articles found! Make sure you ran 002_seed_test_case.sql first.")
        return

    # Process each article
    for article in articles:
        article_num = article.get("article_number")
        text_en = article.get("text_english", "")
        text_ar = article.get("text_arabic", "")

        logger.info(f"\nProcessing Article {article_num}...")

        updates = {}

        # Generate English embedding
        if text_en:
            logger.info(f"  Generating English embedding...")
            try:
                embedding = embed_text(openai_client, text_en)
                updates["embedding"] = embedding
                logger.info(f"  ✓ English embedding ({len(embedding)} dims)")
            except Exception as e:
                logger.error(f"  ✗ English embedding failed: {e}")

        # Generate Arabic embedding
        if text_ar:
            logger.info(f"  Generating Arabic embedding...")
            try:
                arabic_embedding = embed_text(openai_client, text_ar)
                updates["arabic_embedding"] = arabic_embedding
                logger.info(f"  ✓ Arabic embedding ({len(arabic_embedding)} dims)")
            except Exception as e:
                logger.error(f"  ✗ Arabic embedding failed: {e}")

        # Update article in Supabase
        if updates:
            try:
                supabase.table("articles") \
                    .update(updates) \
                    .eq("article_number", article_num) \
                    .execute()
                logger.info(f"  ✓ Saved to database")
            except Exception as e:
                logger.error(f"  ✗ Database update failed: {e}")

        # Rate limiting
        time.sleep(0.2)

    logger.info("\n" + "=" * 60)
    logger.info("✓ EMBEDDING GENERATION COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
