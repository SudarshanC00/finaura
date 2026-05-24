"""
Multi-Vector Indexing with Qdrant and Recursive Retrieval.

Creates a Qdrant-backed vector index where summary nodes are embedded
for search, but the actual raw table data is retrieved via IndexNode linking.

Supports per-document collections for multi-company document management.
"""

import logging
import os
from typing import Optional

import qdrant_client
from llama_index.core import (
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.retrievers import RecursiveRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore

from config import (
    DEFAULT_COLLECTION_NAME,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    OPENAI_API_BASE,
    QDRANT_PATH,
    SIMILARITY_TOP_K,
)

logger = logging.getLogger(__name__)

BASE_PERSIST_DIR = "./storage/index"


def get_persist_dir(collection_name: str) -> str:
    """Get the persist directory for a specific collection."""
    return os.path.join(BASE_PERSIST_DIR, collection_name)


def get_qdrant_client() -> qdrant_client.QdrantClient:
    """Create a local Qdrant client with persistent storage."""
    os.makedirs(QDRANT_PATH, exist_ok=True)
    return qdrant_client.QdrantClient(path=QDRANT_PATH)


def get_embedding_model() -> OpenAIEmbedding:
    """Initialize the OpenAI embedding model."""
    return OpenAIEmbedding(
        model=EMBEDDING_MODEL,
        dimensions=EMBEDDING_DIM,
        api_base=OPENAI_API_BASE,
    )


def create_index(
    nodes: list,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> VectorStoreIndex:
    """
    Build a Qdrant-backed VectorStoreIndex from ingested nodes.

    The index contains:
    - TextNodes for narrative text chunks (directly embedded and retrieved)
    - IndexNodes for table summaries (embedded for search)
    - TextNodes for table details (retrieved via IndexNode linking)
    """
    logger.info(f"Creating Qdrant index with {len(nodes)} nodes (collection: {collection_name})...")

    client = get_qdrant_client()
    embed_model = get_embedding_model()

    # Delete existing collection if it exists (fresh ingest)
    try:
        client.delete_collection(collection_name)
        logger.info(f"Deleted existing collection: {collection_name}")
    except Exception:
        pass

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        dimension=EMBEDDING_DIM,
    )

    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    storage_context.docstore.add_documents(nodes)

    index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )

    # Persist the docstore and index metadata locally
    persist_dir = get_persist_dir(collection_name)
    os.makedirs(persist_dir, exist_ok=True)
    index.storage_context.persist(persist_dir=persist_dir)
    logger.info(f"Index persisted to {persist_dir}")

    return index


def load_index(
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Optional[VectorStoreIndex]:
    """
    Load a previously persisted index from disk + Qdrant.
    Returns None if no index exists.
    """
    persist_dir = get_persist_dir(collection_name)
    if not os.path.exists(persist_dir) or not os.path.exists(QDRANT_PATH):
        logger.warning(f"No persisted index found for collection: {collection_name}")
        return None

    try:
        client = get_qdrant_client()
        embed_model = get_embedding_model()

        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            dimension=EMBEDDING_DIM,
        )

        storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
            persist_dir=persist_dir,
        )

        index = load_index_from_storage(
            storage_context=storage_context,
            embed_model=embed_model,
        )

        logger.info(f"Successfully loaded existing index for collection: {collection_name}")
        return index

    except Exception as e:
        logger.error(f"Failed to load index: {e}")
        return None


def load_or_create_index(
    nodes: Optional[list] = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> VectorStoreIndex:
    """
    Load existing index or create a new one if nodes are provided.
    """
    if nodes:
        return create_index(nodes, collection_name=collection_name)

    index = load_index(collection_name=collection_name)
    if index is None:
        raise ValueError(
            f"No existing index found for collection '{collection_name}' and no nodes provided. "
            "Run ingestion first."
        )
    return index


def build_recursive_retriever(index: VectorStoreIndex) -> RecursiveRetriever:
    """
    Build a RecursiveRetriever that:
    1. Searches the vector index for matching summary/text nodes
    2. When an IndexNode (table summary) is matched, automatically
       retrieves the linked detail node (raw Markdown table)

    This gives us: searchability of summaries + precision of raw data.
    """
    # The vector retriever searches over all embedded nodes
    vector_retriever = index.as_retriever(
        similarity_top_k=SIMILARITY_TOP_K,
    )

    # Build a mapping of node_id -> node for all nodes in the docstore
    all_nodes_dict = {}
    docstore = index.storage_context.docstore

    # Get all nodes from docstore
    nodes = list(docstore.docs.values())
    for node in nodes:
        all_nodes_dict[node.node_id] = node

    logger.info(f"Recursive retriever initialized with {len(all_nodes_dict)} nodes in node_dict")

    recursive_retriever = RecursiveRetriever(
        "vector",
        retriever_dict={"vector": vector_retriever},
        node_dict=all_nodes_dict,
        verbose=True,
    )

    return recursive_retriever
