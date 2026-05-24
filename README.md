---
title: Finaura - Financial RAG
emoji: 📊
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-16-000000?style=for-the-badge&logo=next.js&logoColor=white" />
  <img src="https://img.shields.io/badge/TypeScript-5-3178c6?style=for-the-badge&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/LlamaIndex-0.12+-purple?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Qdrant-Vector_DB-dc382d?style=for-the-badge" />
</p>

<h1 align="center">📊 Financial RAG Analyst</h1>

<p align="center">
  <strong>AI-powered financial document analysis platform.</strong><br/>
  Upload SEC filings from <em>any company</em> and get instant, cited, analyst-grade answers.
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#%EF%B8%8F-architecture">Architecture</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-api-reference">API</a> •
  <a href="#-tech-stack">Tech Stack</a>
</p>

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **Multi-Company Support** | Upload 10-K, 10-Q, or annual reports from **any company** — not locked to a single filing |
| 🧠 **Intelligent Table Extraction** | Docling-powered PDF parsing with layout analysis separates tables from narrative text |
| 🔍 **Recursive Retrieval** | Table summaries are embedded for search; raw table data is retrieved for precision (best of both worlds) |
| 💬 **Chat Interface** | Ask questions in natural language and get **Markdown-formatted, cited responses** with financial tables |
| 📊 **Financial Formatting** | Automatic unit multiplier detection — values like `124,300` in "millions" are reported as `$124.30 Billion` |
| 📌 **Page Citations** | Every factual claim includes a page reference: `(Page 17)` — fully verifiable |
| 🛡️ **Guardrails** | Refuses to hallucinate or answer questions outside the uploaded document's scope |
| ⚡ **Background Processing** | PDF ingestion runs asynchronously — upload and check back when it's ready |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                         │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ Sidebar  │  │ Upload Modal │  │ Chat Interface            │  │
│  │ (docs)   │  │ (drag+drop)  │  │ (markdown + tables)       │  │
│  └──────────┘  └──────────────┘  └───────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP (REST)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ /upload    │  │ /query     │  │ /documents │  │ /health   │ │
│  └─────┬──────┘  └─────┬──────┘  └────────────┘  └───────────┘ │
│        │               │                                        │
│        ▼               ▼                                        │
│  ┌───────────┐  ┌──────────────┐                                │
│  │ Ingestion │  │ Query Engine │                                │
│  │ Pipeline  │  │ (GPT-4o)     │                                │
│  └─────┬─────┘  └──────┬───────┘                                │
│        │               │                                        │
│        ▼               ▼                                        │
│  ┌──────────────────────────────────────┐                       │
│  │    Qdrant Vector Store (per-doc)     │                       │
│  │  ┌─────────────┐ ┌────────────────┐  │                       │
│  │  │ Text Chunks │ │ Table Summaries│  │                       │
│  │  └─────────────┘ └───────┬────────┘  │                       │
│  │                          │ IndexNode │                       │
│  │                          ▼ linking   │                       │
│  │                 ┌────────────────┐   │                       │
│  │                 │ Raw Table Data │   │                       │
│  │                 └────────────────┘   │                       │
│  └──────────────────────────────────────┘                       │
└──────────────────────────────────────────────────────────────────┘
```

### How It Works

1. **Upload** — User uploads a financial PDF via the frontend
2. **Ingest** — [Docling](https://github.com/DS4SD/docling) parses the PDF with layout analysis, separating tables from narrative text
3. **Summarize** — Each table is summarized by GPT-4o-mini; the summary becomes the searchable embedding, while the raw Markdown table is stored for retrieval
4. **Index** — All nodes (text chunks + table summary/detail pairs) are embedded using `text-embedding-3-large` (3072 dims) and stored in **Qdrant**
5. **Query** — When a user asks a question, **RecursiveRetriever** searches summaries first, then automatically fetches linked raw table data for precision
6. **Synthesize** — GPT-4o applies financial analyst rules (multiplier formatting, YoY comparison formulas, citations, guardrails) and returns a Markdown response

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 20+**
- **OpenAI API key** (direct) or **OpenRouter API key** (for model routing)

### 1. Clone the repo

```bash
git clone https://github.com/SudarshanC00/Financial-RAG.git
cd Financial-RAG
```

### 2. Set up the backend

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install fastapi uvicorn python-multipart

# Configure API key
cp .env.example .env
# Edit .env and add your API key:
#   OPENAI_API_KEY="sk-your-key-here"           (direct OpenAI)
#   OPENAI_API_KEY="sk-or-v1-your-key-here"     (OpenRouter — auto-detected)
```

### 3. Set up the frontend

```bash
cd frontend
npm install
cd ..
```

### 4. Run both servers

Open **two terminals**:

```bash
# Terminal 1 — API Server (port 8000)
source .venv/bin/activate
uvicorn api:app --host 0.0.0.0 --port 8000
```

```bash
# Terminal 2 — Next.js Frontend (port 3000)
cd frontend
npm run dev
```

### 5. Open the app

Navigate to **http://localhost:3000** in your browser.

---

## 📖 Usage

### Upload a Document

1. Click **"Upload Document"** in the sidebar or landing page
2. Drag-and-drop (or click to select) any financial PDF
3. Fill in the **Company Name** (required), and optionally the document title and filing date
4. Click **"Upload & Process"** — ingestion runs in the background
5. The sidebar shows real-time status: `uploading` → `processing` → `ready`

### Ask Questions

Once a document shows **"ready"**, click it to open the chat interface:

- **Free-form questions**: *"What was the total revenue for Q1 2026?"*
- **Comparison queries**: *"Compare net income year-over-year"*
- **Table extraction**: *"Break down operating expenses by category"*
- **Risk analysis**: *"What are the key risk factors mentioned?"*

Responses include:
- 📊 **Formatted financial tables** (Markdown)
- 📌 **Page citations** for every claim
- 💰 **Automatic unit conversion** (millions → billions)
- 🛡️ **Guardrails** when data isn't available

### CLI Mode (Optional)

You can still use the original CLI for quick testing:

```bash
# Ingest a PDF
python main.py ingest --pdf data/your-filing.pdf

# Interactive query REPL
python main.py query

# One-shot query
python main.py query --single "What was total revenue?"
```

---

## 📡 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | `GET` | Health check + API key status |
| `/api/documents` | `GET` | List all uploaded documents |
| `/api/documents/{id}` | `GET` | Get a specific document's details |
| `/api/documents/upload` | `POST` | Upload PDF (`multipart/form-data`: `file`, `company_name`, `document_title`, `document_date`) |
| `/api/documents/{id}` | `DELETE` | Delete a document and its index |
| `/api/query` | `POST` | Query a document (`JSON`: `{ "question": "...", "document_id": "..." }`) |

Interactive API docs available at **http://localhost:8000/docs** (Swagger UI).

---

## 🛠 Tech Stack

### Backend

| Technology | Purpose |
|---|---|
| **[LlamaIndex](https://docs.llamaindex.ai/)** | Orchestration framework — indexing, retrieval, query engine |
| **[Docling](https://github.com/DS4SD/docling)** | PDF parsing with layout analysis, table structure extraction, OCR |
| **[Qdrant](https://qdrant.tech/)** | Vector database (local, persistent, per-document collections) |
| **[FastAPI](https://fastapi.tiangolo.com/)** | REST API with async support, background tasks, auto-docs |
| **GPT-4o** | Primary reasoning LLM for financial analysis |
| **GPT-4o-mini** | Fast table summarization during ingestion |
| **text-embedding-3-large** | 3072-dimensional embeddings for high-fidelity financial search |

### Frontend

| Technology | Purpose |
|---|---|
| **[Next.js 16](https://nextjs.org/)** | React framework with App Router, SSR |
| **TypeScript** | Type-safe frontend development |
| **[react-markdown](https://github.com/remarkjs/react-markdown)** | Renders Markdown responses (tables, code, lists) |
| **[remark-gfm](https://github.com/remarkjs/remark-gfm)** | GitHub Flavored Markdown support (tables, strikethrough) |
| **[react-dropzone](https://react-dropzone.js.org/)** | Drag-and-drop file upload |

---

## 📁 Project Structure

```
Financial-RAG/
├── api.py                  # FastAPI REST API server
├── main.py                 # CLI entry point (ingest / query)
├── config.py               # Configuration (models, embeddings, Qdrant)
├── ingest.py               # PDF ingestion pipeline (Docling + table summarization)
├── indexer.py              # Qdrant indexing + RecursiveRetriever
├── query_engine.py         # Financial analyst prompt + query engine
├── requirements.txt        # Python dependencies
├── .env.example            # API key template
│
├── frontend/               # Next.js + TypeScript frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx          # Root layout
│   │   │   ├── page.tsx            # Landing page
│   │   │   ├── globals.css         # Dark premium theme
│   │   │   └── chat/
│   │   │       └── [docId]/
│   │   │           └── page.tsx    # Chat interface
│   │   ├── components/
│   │   │   ├── Sidebar.tsx         # Document list sidebar
│   │   │   ├── UploadModal.tsx     # PDF upload modal
│   │   │   └── ChatMessage.tsx     # Message bubble with markdown
│   │   └── lib/
│   │       ├── api.ts              # API client
│   │       └── types.ts            # TypeScript interfaces
│   └── package.json
│
├── storage/                # (gitignored) Qdrant data + index persistence
└── data/                   # (gitignored) Uploaded PDFs
```

---

## ⚙️ Configuration

All configuration lives in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `REASONING_LLM` | `gpt-4o` | Primary LLM for query synthesis |
| `VISION_LLM` | `gpt-4o-mini` | Fast LLM for table summarization |
| `EMBEDDING_MODEL` | `text-embedding-3-large` | Embedding model (3072 dims) |
| `CHUNK_SIZE` | `1024` | Text chunk size for narrative content |
| `CHUNK_OVERLAP` | `128` | Overlap between chunks |
| `SIMILARITY_TOP_K` | `6` | Number of similar nodes to retrieve |

### Using OpenRouter

If your API key starts with `sk-or-`, the system automatically routes through [OpenRouter](https://openrouter.ai/), giving you access to multiple model providers. Otherwise, it connects directly to OpenAI.

---

## 🔑 Key Design Decisions

### Why RecursiveRetriever?

Financial tables are notoriously hard to search because column headers and row labels don't naturally form good embeddings. Our approach:

1. **Summarize tables** → GPT-4o-mini generates a natural language summary ("This table shows quarterly revenue broken down by product segment...")
2. **Embed the summary** → The summary vector is what gets searched
3. **Link to raw data** → When matched, the original Markdown table (with exact numbers) is retrieved via `IndexNode` linking

This gives **semantic searchability** of table content while preserving **numerical precision** for the LLM.

### Why Per-Document Collections?

Each uploaded document gets its own Qdrant collection. This provides:
- **Isolation** — Queries only search within the relevant document
- **Clean deletion** — Removing a document removes only its vectors
- **No cross-contamination** — Apple's financials won't bleed into Nvidia's answers

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<p align="center">
  Built with ❤️ using LlamaIndex, Qdrant, FastAPI, and Next.js
</p>
