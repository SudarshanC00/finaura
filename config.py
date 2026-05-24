"""
Configuration for the Financial RAG Pipeline.
All API keys are loaded from environment variables.
"""

import os
from dotenv import load_dotenv
import llama_index.llms.openai.utils as openai_utils

load_dotenv()

# ── Monkeypatch LlamaIndex Model Validator ────────────────────────────────────
# LlamaIndex hardcodes OpenAI model names. We bypass it so OpenRouter aliases work.
_original_context_fetcher = openai_utils.openai_modelname_to_contextsize

def _safe_context_size(model_name: str) -> int:
    try:
        return _original_context_fetcher(model_name)
    except ValueError:
        return 4096

openai_utils.openai_modelname_to_contextsize = _safe_context_size

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = "https://openrouter.ai/api/v1" if OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-or-") else None

# ── LLM Models ────────────────────────────────────────────────────────────────
# ── LLM Models ────────────────────────────────────────────────────────────────
REASONING_LLM = "openai/gpt-oss-120b:free"                    # Primary reasoning LLM
VISION_LLM = "openai/gpt-oss-120b:free"                  # Fast table summarization
EMBEDDING_MODEL = "nvidia/llama-nemotron-embed-vl-1b-v2:free"   # High-dimensional financial embeddings
EMBEDDING_DIM = 2048                         # Dimensions for nemotron-embed

# ── Qdrant Vector Store ───────────────────────────────────────────────────────
QDRANT_PATH = "./storage/qdrant"
DEFAULT_COLLECTION_NAME = "financial_docs"

# ── Chunking Parameters ──────────────────────────────────────────────────────
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

# ── Retrieval Parameters ──────────────────────────────────────────────────────
SIMILARITY_TOP_K = 3

# ── Unit Multiplier Patterns ─────────────────────────────────────────────────
MULTIPLIER_PATTERNS = {
    r"[Ii]n\s+millions":   1_000_000,
    r"[Ii]n\s+thousands":  1_000,
    r"[Ii]n\s+billions":   1_000_000_000,
}
