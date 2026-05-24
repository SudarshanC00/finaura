"""
Configuration for the Financial RAG Pipeline.
All API keys are loaded from environment variables.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = "https://openrouter.ai/api/v1" if OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-or-") else None

# ── LLM Models ────────────────────────────────────────────────────────────────
REASONING_LLM = "gpt-4o"                    # Primary reasoning LLM
VISION_LLM = "gpt-4o-mini"                  # Fast table summarization
EMBEDDING_MODEL = "text-embedding-3-large"   # High-dimensional financial embeddings
EMBEDDING_DIM = 3072                         # Dimensions for text-embedding-3-large

# ── Qdrant Vector Store ───────────────────────────────────────────────────────
QDRANT_PATH = "./storage/qdrant"
DEFAULT_COLLECTION_NAME = "financial_docs"

# ── Chunking Parameters ──────────────────────────────────────────────────────
CHUNK_SIZE = 1024
CHUNK_OVERLAP = 128

# ── Retrieval Parameters ──────────────────────────────────────────────────────
SIMILARITY_TOP_K = 6

# ── Unit Multiplier Patterns ─────────────────────────────────────────────────
MULTIPLIER_PATTERNS = {
    r"[Ii]n\s+millions":   1_000_000,
    r"[Ii]n\s+thousands":  1_000,
    r"[Ii]n\s+billions":   1_000_000_000,
}
