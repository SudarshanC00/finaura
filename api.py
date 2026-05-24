"""
FastAPI REST API for the Financial RAG Pipeline.

Exposes ingestion, querying, document management, and chat persistence
as REST endpoints that the Next.js frontend consumes.
"""

import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Financial RAG API",
    description="API for uploading and querying financial documents",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://financial-rag-k397.onrender.com",
    ],
    allow_origin_regex=r"https://.*\.(vercel\.app|hf\.space)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Storage Paths ────────────────────────────────────────────────────────────

DOCUMENTS_DIR = "./storage/documents"
UPLOADS_DIR = "./storage/uploads"
CHATS_DIR = "./storage/chats"
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(CHATS_DIR, exist_ok=True)


# ─── Models ───────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    document_id: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict] = []
    chart_data: Optional[dict] = None


class DocumentInfo(BaseModel):
    id: str
    filename: str
    company_name: str
    document_title: str
    document_date: str
    status: str  # "uploading", "processing", "ready", "error"
    created_at: str
    file_size: int = 0
    error_message: str = ""


class ChatMessageModel(BaseModel):
    id: str
    role: str  # "user" | "assistant"
    content: str
    sources: list[dict] = []
    chart_data: Optional[dict] = None
    timestamp: str


class ChatInfo(BaseModel):
    id: str
    document_id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[ChatMessageModel] = []


class ChatSummary(BaseModel):
    """Chat info without messages, for listing."""
    id: str
    document_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class ChatSendRequest(BaseModel):
    question: str


# ─── Chart Data Extraction ────────────────────────────────────────────────────

import re as _re

def _extract_chart_data(text: str) -> tuple[str, Optional[dict]]:
    """
    Extract ```chart ... ``` fenced code block from LLM response.
    Returns (cleaned_text, chart_data_dict_or_None).
    """
    pattern = r'```chart\s*\n?(.*?)\n?```'
    match = _re.search(pattern, text, _re.DOTALL)
    if not match:
        return text, None

    chart_json_str = match.group(1).strip()
    cleaned_text = text[:match.start()].rstrip() + text[match.end():].lstrip()

    try:
        chart_data = json.loads(chart_json_str)
        # Validate minimum structure
        if isinstance(chart_data, dict) and "type" in chart_data and "data" in chart_data:
            return cleaned_text, chart_data
    except (json.JSONDecodeError, ValueError):
        logger.warning(f"Failed to parse chart JSON: {chart_json_str[:200]}")

    return cleaned_text, None


# ─── Document Metadata Helpers ──────────────────────────────────────���─────────

def _get_doc_meta_path(doc_id: str) -> str:
    return os.path.join(DOCUMENTS_DIR, f"{doc_id}.json")


def _save_doc_meta(doc: DocumentInfo):
    with open(_get_doc_meta_path(doc.id), "w") as f:
        json.dump(doc.model_dump(), f, indent=2)


def _load_doc_meta(doc_id: str) -> Optional[DocumentInfo]:
    path = _get_doc_meta_path(doc_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return DocumentInfo(**json.load(f))


def _get_collection_name(doc_id: str) -> str:
    """Generate a Qdrant collection name from document ID."""
    return f"doc_{doc_id.replace('-', '_')}"


# ─── Chat Persistence Helpers ─────────────────────────────────────────────────

def _get_chat_path(chat_id: str) -> str:
    return os.path.join(CHATS_DIR, f"{chat_id}.json")


def _save_chat(chat: ChatInfo):
    with open(_get_chat_path(chat.id), "w") as f:
        json.dump(chat.model_dump(), f, indent=2)


def _load_chat(chat_id: str) -> Optional[ChatInfo]:
    path = _get_chat_path(chat_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return ChatInfo(**json.load(f))


def _list_chats_for_doc(doc_id: str) -> list[ChatSummary]:
    """List all chats belonging to a document."""
    chats = []
    if os.path.exists(CHATS_DIR):
        for filename in os.listdir(CHATS_DIR):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(CHATS_DIR, filename)
            try:
                with open(path) as f:
                    data = json.load(f)
                if data.get("document_id") == doc_id:
                    chats.append(ChatSummary(
                        id=data["id"],
                        document_id=data["document_id"],
                        title=data["title"],
                        created_at=data["created_at"],
                        updated_at=data["updated_at"],
                        message_count=len(data.get("messages", [])),
                    ))
            except Exception:
                continue
    chats.sort(key=lambda c: c.updated_at, reverse=True)
    return chats


def _delete_chats_for_doc(doc_id: str):
    """Delete all chats belonging to a document."""
    if os.path.exists(CHATS_DIR):
        for filename in os.listdir(CHATS_DIR):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(CHATS_DIR, filename)
            try:
                with open(path) as f:
                    data = json.load(f)
                if data.get("document_id") == doc_id:
                    os.remove(path)
            except Exception:
                continue


# ─── AI Chat Title Generation ─────────────────────────────────────────────────

def _generate_chat_title(question: str, answer: str) -> str:
    """Use LLM to generate a short, descriptive chat title from the first Q&A."""
    try:
        from llama_index.llms.openai import OpenAI
        from config import OPENAI_API_BASE, VISION_LLM

        llm = OpenAI(
            model=VISION_LLM,
            api_base=OPENAI_API_BASE,
            temperature=0.0,
            max_tokens=30,
        )

        prompt = (
            "Generate a very short chat title (max 6 words) that summarizes this financial Q&A. "
            "Return ONLY the title, no quotes, no punctuation at the end.\n\n"
            f"Question: {question[:200]}\n"
            f"Answer snippet: {answer[:300]}\n\n"
            "Title:"
        )

        response = llm.complete(prompt)
        title = response.text.strip().strip('"\'').strip()

        # Fallback if LLM returns empty or too long
        if not title or len(title) > 80:
            title = question[:60] + ("..." if len(question) > 60 else "")

        return title

    except Exception as e:
        logger.warning(f"Failed to generate AI title: {e}")
        # Fallback to truncated question
        return question[:60] + ("..." if len(question) > 60 else "")


# ─── Background Ingestion Task ───────────────────────────────────────────────

def _run_ingestion(doc_id: str, pdf_path: str, document_title: str, document_date: str):
    """Background task: ingest PDF and build vector index."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # Set up logging for background tasks
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    doc = _load_doc_meta(doc_id)
    if not doc:
        logger.error(f"Document {doc_id} not found during ingestion")
        return

    try:
        doc.status = "processing"
        _save_doc_meta(doc)

        # Step 1: Ingest PDF
        from ingest import ingest_pdf
        nodes = ingest_pdf(
            pdf_path=pdf_path,
            document_title=document_title,
            document_date=document_date,
        )

        if not nodes:
            doc.status = "error"
            doc.error_message = "No content extracted from PDF"
            _save_doc_meta(doc)
            return

        # Step 2: Build index
        from indexer import create_index
        collection_name = _get_collection_name(doc_id)
        create_index(nodes, collection_name=collection_name)

        doc.status = "ready"
        _save_doc_meta(doc)
        logger.info(f"Document {doc_id} ingestion complete: {len(nodes)} nodes indexed")

    except Exception as e:
        logger.error(f"Ingestion failed for {doc_id}: {e}", exc_info=True)
        doc.status = "error"
        doc.error_message = str(e)
        _save_doc_meta(doc)


# ─── API Endpoints ─────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "api_key_set": bool(OPENAI_API_KEY)}


@app.get("/api/documents", response_model=list[DocumentInfo])
async def list_documents():
    """List all ingested documents."""
    documents = []
    if os.path.exists(DOCUMENTS_DIR):
        for filename in sorted(os.listdir(DOCUMENTS_DIR)):
            if filename.endswith(".json"):
                path = os.path.join(DOCUMENTS_DIR, filename)
                with open(path) as f:
                    documents.append(DocumentInfo(**json.load(f)))
    # Sort by created_at descending
    documents.sort(key=lambda d: d.created_at, reverse=True)
    return documents


@app.get("/api/documents/{doc_id}", response_model=DocumentInfo)
async def get_document(doc_id: str):
    """Get a specific document's details."""
    doc = _load_doc_meta(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.post("/api/documents/upload", response_model=DocumentInfo)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    company_name: str = Form(...),
    document_title: str = Form(""),
    document_date: str = Form(""),
):
    """
    Upload a financial PDF document for processing.
    Ingestion runs in the background.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    doc_id = str(uuid.uuid4())[:8]

    # Determine document title
    if not document_title:
        base_name = f"{company_name}" if company_name else "Filing"
        document_title = f"{base_name} - {file.filename}"

    # Save uploaded file
    upload_path = os.path.join(UPLOADS_DIR, f"{doc_id}_{file.filename}")
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Create document metadata
    doc = DocumentInfo(
        id=doc_id,
        filename=file.filename,
        company_name=company_name,
        document_title=document_title,
        document_date=document_date,
        status="uploading",
        created_at=datetime.now().isoformat(),
        file_size=len(content),
    )
    _save_doc_meta(doc)

    # Start background ingestion
    background_tasks.add_task(
        _run_ingestion,
        doc_id=doc_id,
        pdf_path=upload_path,
        document_title=document_title,
        document_date=document_date,
    )

    return doc


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document, its index, and all associated chats."""
    doc = _load_doc_meta(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove metadata
    meta_path = _get_doc_meta_path(doc_id)
    if os.path.exists(meta_path):
        os.remove(meta_path)

    # Remove upload file
    for f in os.listdir(UPLOADS_DIR):
        if f.startswith(doc_id):
            os.remove(os.path.join(UPLOADS_DIR, f))

    # Remove index persist dir
    from indexer import get_persist_dir
    collection_name = _get_collection_name(doc_id)
    persist_dir = get_persist_dir(collection_name)
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)

    # Try to delete Qdrant collection
    try:
        from indexer import get_qdrant_client
        client = get_qdrant_client()
        client.delete_collection(collection_name)
    except Exception:
        pass

    # Delete all associated chats
    _delete_chats_for_doc(doc_id)

    return {"status": "deleted", "id": doc_id}


@app.post("/api/query", response_model=QueryResponse)
async def query_document(request: QueryRequest):
    """Query a specific document."""
    doc = _load_doc_meta(request.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Document is not ready for querying (status: {doc.status})"
        )

    try:
        from indexer import build_recursive_retriever, load_index
        from query_engine import build_query_engine, format_response

        collection_name = _get_collection_name(request.document_id)
        index = load_index(collection_name=collection_name)
        if index is None:
            raise HTTPException(status_code=500, detail="Index not found for this document")

        retriever = build_recursive_retriever(index)
        engine = build_query_engine(
            retriever,
            document_title=doc.document_title,
            document_date=doc.document_date,
        )

        response = engine.query(request.question)
        formatted = format_response(response)

        # Extract chart data if present
        formatted, chart_data = _extract_chart_data(formatted)

        # Extract source info
        sources = []
        if hasattr(response, 'source_nodes') and response.source_nodes:
            for node in response.source_nodes:
                meta = node.metadata if hasattr(node, 'metadata') else {}
                sources.append({
                    "page": meta.get("page_label", "?"),
                    "section": meta.get("section_title", "?"),
                    "is_table": meta.get("is_table", False),
                })

        return QueryResponse(answer=formatted, sources=sources, chart_data=chart_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# ─── Chat Endpoints ────────────────────────────────────��───────────────────────

@app.get("/api/documents/{doc_id}/chats", response_model=list[ChatSummary])
async def list_chats(doc_id: str):
    """List all chats for a document."""
    doc = _load_doc_meta(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _list_chats_for_doc(doc_id)


@app.post("/api/documents/{doc_id}/chats", response_model=ChatInfo)
async def create_chat(doc_id: str):
    """Create a new chat for a document."""
    doc = _load_doc_meta(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chat = ChatInfo(
        id=str(uuid.uuid4())[:8],
        document_id=doc_id,
        title="New Chat",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        messages=[],
    )
    _save_chat(chat)
    return chat


@app.get("/api/chats/{chat_id}", response_model=ChatInfo)
async def get_chat(chat_id: str):
    """Get a chat with all messages."""
    chat = _load_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat."""
    path = _get_chat_path(chat_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Chat not found")
    os.remove(path)
    return {"status": "deleted", "id": chat_id}


@app.patch("/api/chats/{chat_id}")
async def update_chat(chat_id: str, payload: dict):
    """Update chat metadata (e.g., title)."""
    chat = _load_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if "title" in payload:
        chat.title = payload["title"]
    chat.updated_at = datetime.now().isoformat()
    _save_chat(chat)
    return chat


@app.post("/api/chats/{chat_id}/generate-title")
async def generate_title(chat_id: str):
    """Use AI to generate a title from the chat's conversation."""
    chat = _load_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if not chat.messages:
        raise HTTPException(status_code=400, detail="Chat has no messages")

    # Find the first user question and assistant answer
    first_q = ""
    first_a = ""
    for msg in chat.messages:
        if msg.role == "user" and not first_q:
            first_q = msg.content
        elif msg.role == "assistant" and not first_a and first_q:
            first_a = msg.content
            break

    if not first_q:
        raise HTTPException(status_code=400, detail="No user messages found")

    title = _generate_chat_title(first_q, first_a)
    chat.title = title
    chat.updated_at = datetime.now().isoformat()
    _save_chat(chat)
    return {"title": title}


@app.post("/api/chats/{chat_id}/messages", response_model=QueryResponse)
async def send_chat_message(chat_id: str, request: ChatSendRequest):
    """
    Send a message in a chat. Persists user + assistant messages,
    queries the document's RAG index, and returns the answer.
    """
    chat = _load_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    doc = _load_doc_meta(chat.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Document is not ready for querying (status: {doc.status})",
        )

    # Add user message
    user_msg = ChatMessageModel(
        id=str(uuid.uuid4())[:8],
        role="user",
        content=request.question,
        sources=[],
        timestamp=datetime.now().isoformat(),
    )
    chat.messages.append(user_msg)

    # Query the RAG pipeline
    try:
        from indexer import build_recursive_retriever, load_index
        from query_engine import build_query_engine, format_response

        collection_name = _get_collection_name(chat.document_id)
        index = load_index(collection_name=collection_name)
        if index is None:
            raise HTTPException(status_code=500, detail="Index not found for this document")

        retriever = build_recursive_retriever(index)
        engine = build_query_engine(
            retriever,
            document_title=doc.document_title,
            document_date=doc.document_date,
        )

        response = engine.query(request.question)
        formatted = format_response(response)

        # Extract chart data if present
        formatted, chart_data = _extract_chart_data(formatted)

        # Extract source info
        sources = []
        if hasattr(response, "source_nodes") and response.source_nodes:
            for node in response.source_nodes:
                meta = node.metadata if hasattr(node, "metadata") else {}
                sources.append({
                    "page": meta.get("page_label", "?"),
                    "section": meta.get("section_title", "?"),
                    "is_table": meta.get("is_table", False),
                })

        # Add assistant message
        assistant_msg = ChatMessageModel(
            id=str(uuid.uuid4())[:8],
            role="assistant",
            content=formatted,
            sources=sources,
            chart_data=chart_data,
            timestamp=datetime.now().isoformat(),
        )
        chat.messages.append(assistant_msg)

        # Auto-title: use LLM to generate a concise title after first exchange
        if chat.title == "New Chat" and request.question:
            chat.title = _generate_chat_title(request.question, formatted)

        chat.updated_at = datetime.now().isoformat()
        _save_chat(chat)

        return QueryResponse(answer=formatted, sources=sources, chart_data=chart_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/api/chats", response_model=list[ChatSummary])
async def list_all_chats():
    """List all chats across all documents."""
    chats = []
    if os.path.exists(CHATS_DIR):
        for filename in os.listdir(CHATS_DIR):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(CHATS_DIR, filename)
            try:
                with open(path) as f:
                    data = json.load(f)
                chats.append(ChatSummary(
                    id=data["id"],
                    document_id=data["document_id"],
                    title=data["title"],
                    created_at=data["created_at"],
                    updated_at=data["updated_at"],
                    message_count=len(data.get("messages", [])),
                ))
            except Exception:
                continue
    chats.sort(key=lambda c: c.updated_at, reverse=True)
    return chats


# ─── Run with Uvicorn ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
