"""Legal Search Agent Components."""
from .decomposer import Decomposer
from .retriever import ArticleRetriever
from .synthesizer import Synthesizer

# Agentic RAG components
from .hyde_generator import HydeGenerator
from .coverage_analyzer import CoverageAnalyzer
from .crossref_expander import CrossRefExpander
from .retrieval_agent import RetrievalAgent

__all__ = [
    # Core components
    "Decomposer",
    "ArticleRetriever",  # Legacy retriever (kept for reference)
    "Synthesizer",
    # Agentic RAG components
    "HydeGenerator",
    "CoverageAnalyzer",
    "CrossRefExpander",
    "RetrievalAgent",
]
