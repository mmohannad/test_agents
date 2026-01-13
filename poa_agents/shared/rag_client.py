"""
RAG Client for legal article retrieval.
Uses semantic search over the articles table.
"""

import os
from typing import Optional
from dataclasses import dataclass

from .llm_client import LLMClient, get_llm_client
from .supabase_client import get_supabase_client


@dataclass
class Article:
    """A retrieved legal article."""
    article_number: int
    text_arabic: Optional[str]
    text_english: Optional[str]
    hierarchy_path: Optional[dict]
    similarity: float
    
    @property
    def text(self) -> str:
        """Return English text if available, otherwise Arabic."""
        return self.text_english or self.text_arabic or ""
    
    def to_context_string(self) -> str:
        """Format article for inclusion in LLM context."""
        hierarchy = ""
        if self.hierarchy_path:
            parts = []
            if self.hierarchy_path.get("law"):
                parts.append(f"Law: {self.hierarchy_path['law']}")
            if self.hierarchy_path.get("chapter"):
                parts.append(f"Chapter: {self.hierarchy_path['chapter']}")
            if self.hierarchy_path.get("section"):
                parts.append(f"Section: {self.hierarchy_path['section']}")
            hierarchy = " > ".join(parts)
        
        return f"""
Article {self.article_number}
{f"({hierarchy})" if hierarchy else ""}

{self.text}
---
"""


class RAGClient:
    """Client for retrieving relevant legal articles via semantic search."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        similarity_threshold: float = 0.3,
        default_limit: int = 5,
    ):
        self.llm = llm_client or get_llm_client()
        self.supabase = get_supabase_client()
        self.similarity_threshold = similarity_threshold
        self.default_limit = default_limit
    
    async def retrieve_articles(
        self,
        query: str,
        limit: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ) -> list[Article]:
        """
        Retrieve relevant articles using semantic search.
        
        Args:
            query: The search query (will be embedded)
            limit: Maximum number of articles to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of relevant articles sorted by similarity
        """
        # Generate embedding for query
        embedding = await self.llm.get_embedding(query)
        
        # Call the match_articles Supabase function
        result = self.supabase.rpc(
            'match_articles',
            {
                'query_embedding': embedding,
                'match_threshold': similarity_threshold or self.similarity_threshold,
                'match_count': limit or self.default_limit,
            }
        ).execute()
        
        # Convert to Article objects
        articles = []
        for row in result.data or []:
            articles.append(Article(
                article_number=row.get("article_number"),
                text_arabic=row.get("text_arabic"),
                text_english=row.get("text_english"),
                hierarchy_path=row.get("hierarchy_path"),
                similarity=row.get("similarity", 0.0),
            ))
        
        return articles
    
    async def retrieve_articles_for_questions(
        self,
        questions: list[str],
        limit_per_question: int = 3,
    ) -> dict[str, list[Article]]:
        """
        Retrieve articles for multiple questions.
        
        Args:
            questions: List of questions to search for
            limit_per_question: Max articles per question
            
        Returns:
            Dict mapping question to relevant articles
        """
        results = {}
        for question in questions:
            articles = await self.retrieve_articles(
                query=question,
                limit=limit_per_question,
            )
            results[question] = articles
        return results
    
    def format_articles_for_context(
        self,
        articles: list[Article],
        max_chars: int = 8000,
    ) -> str:
        """Format articles as context string for LLM."""
        context_parts = []
        total_chars = 0
        
        for article in articles:
            article_str = article.to_context_string()
            if total_chars + len(article_str) > max_chars:
                break
            context_parts.append(article_str)
            total_chars += len(article_str)
        
        if not context_parts:
            return "No relevant legal articles found."
        
        return "\n".join([
            "=== RELEVANT LEGAL ARTICLES ===",
            *context_parts,
            "=== END OF ARTICLES ==="
        ])


# Singleton instance
_rag_client: Optional[RAGClient] = None


def get_rag_client() -> RAGClient:
    """Get or create the singleton RAG client."""
    global _rag_client
    if _rag_client is None:
        _rag_client = RAGClient()
    return _rag_client

