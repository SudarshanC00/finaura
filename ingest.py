"""
Financial-Aware PDF Ingestion using Docling.

Parses financial PDFs with layout analysis, separates tables from text,
converts tables to Markdown, extracts unit multipliers, and generates
LLM-based summaries for each table to enable recursive retrieval.

Supports any company's financial documents (10-K, 10-Q, Annual Reports).
"""

import logging
import re
import uuid
from typing import Optional

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import DocItemLabel
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import IndexNode, TextNode
from llama_index.llms.openai import OpenAI

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    MULTIPLIER_PATTERNS,
    OPENAI_API_BASE,
    VISION_LLM,
)

logger = logging.getLogger(__name__)


# ─── Unit Multiplier Extraction ───────────────────────────────────────────────

def extract_multiplier(text: str) -> Optional[int]:
    """
    Scan text for unit multiplier phrases like 'In millions'.
    Returns the numeric multiplier or None.
    """
    for pattern, value in MULTIPLIER_PATTERNS.items():
        if re.search(pattern, text):
            return value
    return None


def detect_section_title(text: str) -> str:
    """Heuristic to detect SEC filing section headers."""
    section_patterns = [
        (r"Item\s+1[A-Z]?\.\s+.+", None),
        (r"Item\s+2\.\s+.+", None),
        (r"Item\s+3\.\s+.+", None),
        (r"Item\s+4\.\s+.+", None),
        (r"CONDENSED CONSOLIDATED.+", None),
        (r"NOTES TO CONDENSED.+", None),
    ]
    for pattern, _ in section_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return ""


# ─── Table Summarization ─────────────────────────────────────────────────────

def summarize_table(table_markdown: str, section_title: str, page_num: int) -> str:
    """
    Use GPT-4o-mini to generate a semantic summary of a financial table.
    This summary becomes the searchable vector; the raw table is retrieved.
    """
    llm = OpenAI(
        model=VISION_LLM,
        api_base=OPENAI_API_BASE,
        temperature=0.0,
        max_tokens=1024
    )

    prompt = f"""You are a financial document analyst. Summarize the following financial table
in 2-3 sentences. Include:
- The exact title/type of the table (e.g., "Consolidated Statements of Operations")
- Key financial metrics and their values
- The time periods covered
- The reporting entity name

Section: {section_title}
Page: {page_num}

Table (Markdown):
{table_markdown}

Summary:"""

    response = llm.complete(prompt)
    return response.text.strip()


# ─── Main Ingestion Pipeline ─────────────────────────────────────────────────

def ingest_pdf(
    pdf_path: str,
    document_title: str = "Financial Document",
    document_date: str = "",
) -> list:
    """
    Parse a financial PDF using Docling and return LlamaIndex nodes.

    Args:
        pdf_path: Path to the PDF file
        document_title: Title for the document (e.g., "Apple Inc. 10-K FY2025")
        document_date: Filing date or period (e.g., "Sep 28, 2025")

    Returns a list of nodes:
    - TextNode for narrative text chunks
    - IndexNode (summary) + TextNode (raw table) pairs for tables
    """
    logger.info(f"Starting ingestion of: {pdf_path}")

    # ── Step 1: Docling PDF Conversion ────────────────────────────────────
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_table_structure = True
    pipeline_options.do_ocr = True

    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=PdfPipelineOptions(
                    do_table_structure=True,
                    do_ocr=True,
                )
            )
        },
    )

    result = converter.convert(pdf_path)
    doc = result.document

    logger.info("Docling conversion complete. Processing elements...")

    # ── Step 2: Detect global unit multiplier ─────────────────────────────
    # Scan full document text for the multiplier (usually in header/notes)
    full_text = doc.export_to_markdown()
    global_multiplier = extract_multiplier(full_text)
    if global_multiplier:
        logger.info(f"Detected global unit multiplier: {global_multiplier:,}")
    else:
        logger.warning("No global unit multiplier detected. Defaulting to 1.")
        global_multiplier = 1

    # ── Step 3: Process document elements ─────────────────────────────────
    all_nodes = []
    table_count = 0
    text_count = 0
    current_section = "General"

    for item, _level in doc.iterate_items():
        # Track section titles
        if item.label in (DocItemLabel.SECTION_HEADER, DocItemLabel.TITLE):
            header_text = item.text if hasattr(item, 'text') else ""
            detected = detect_section_title(header_text)
            if detected:
                current_section = detected
            elif header_text:
                current_section = header_text
            continue

        # ── Process Tables ────────────────────────────────────────────
        if item.label == DocItemLabel.TABLE:
            table_count += 1

            # Export table as Markdown
            try:
                table_md = item.export_to_markdown()
            except Exception:
                table_md = item.text if hasattr(item, 'text') else str(item)

            if not table_md or len(table_md.strip()) < 20:
                logger.warning(f"Skipping empty/tiny table in section: {current_section}")
                continue

            # Check for local multiplier in table or nearby text
            local_multiplier = extract_multiplier(table_md)
            multiplier = local_multiplier if local_multiplier else global_multiplier

            # Get page number from Docling provenance
            page_num = _get_page_number(item)

            # Generate summary via LLM
            logger.info(f"  Summarizing table {table_count} (Page {page_num}, Section: {current_section})...")
            summary_text = summarize_table(table_md, current_section, page_num)

            # Create the raw detail node (actual table data)
            detail_node_id = str(uuid.uuid4())
            detail_node = TextNode(
                text=table_md,
                id_=detail_node_id,
                metadata={
                    "page_label": str(page_num),
                    "section_title": current_section,
                    "document_date": document_date,
                    "document_title": document_title,
                    "is_table": True,
                    "multiplier": multiplier,
                    "table_index": table_count,
                    "node_type": "table_detail",
                },
                excluded_embed_metadata_keys=["node_type", "table_index"],
                excluded_llm_metadata_keys=["node_type", "table_index"],
            )

            # Create the summary index node (searchable, points to detail)
            summary_node = IndexNode(
                text=summary_text,
                id_=str(uuid.uuid4()),
                index_id=detail_node_id,
                metadata={
                    "page_label": str(page_num),
                    "section_title": current_section,
                    "document_date": document_date,
                    "document_title": document_title,
                    "is_table": True,
                    "multiplier": multiplier,
                    "table_index": table_count,
                    "node_type": "table_summary",
                },
                excluded_embed_metadata_keys=["node_type", "table_index"],
                excluded_llm_metadata_keys=["node_type", "table_index"],
            )

            all_nodes.extend([detail_node, summary_node])

        # ── Process Text Blocks ───────────────────────────────────────
        elif item.label in (
            DocItemLabel.PARAGRAPH,
            DocItemLabel.LIST_ITEM,
            DocItemLabel.TEXT,
            DocItemLabel.CAPTION,
        ):
            text_content = item.text if hasattr(item, 'text') else ""
            if not text_content or len(text_content.strip()) < 50:
                continue

            page_num = _get_page_number(item)

            # Chunk long text blocks
            splitter = SentenceSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
            )
            chunks = splitter.split_text(text_content)

            for i, chunk in enumerate(chunks):
                text_count += 1
                node = TextNode(
                    text=chunk,
                    id_=str(uuid.uuid4()),
                    metadata={
                        "page_label": str(page_num),
                        "section_title": current_section,
                        "document_date": document_date,
                        "document_title": document_title,
                        "is_table": False,
                        "node_type": "text",
                    },
                    excluded_embed_metadata_keys=["node_type"],
                    excluded_llm_metadata_keys=["node_type"],
                )
                all_nodes.append(node)

    logger.info(f"Ingestion complete: {table_count} tables, {text_count} text chunks")
    logger.info(f"Total nodes created: {len(all_nodes)}")

    return all_nodes


def _get_page_number(item) -> int:
    """Extract page number from a Docling document item."""
    try:
        if hasattr(item, 'prov') and item.prov:
            prov = item.prov[0] if isinstance(item.prov, list) else item.prov
            if hasattr(prov, 'page_no'):
                return prov.page_no
            if hasattr(prov, 'page'):
                return prov.page
    except (IndexError, AttributeError):
        pass
    return 0
