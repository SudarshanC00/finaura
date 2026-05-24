"""
Financial Analyst Query Engine.

Wraps the RecursiveRetriever with a GPT-4o powered query engine
that applies financial formatting rules, comparison logic, citations,
and guardrails for out-of-scope questions.

Supports any company's financial documents dynamically.
"""

import logging

from llama_index.core.prompts import PromptTemplate
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.llms.openai import OpenAI

from config import OPENAI_API_BASE, REASONING_LLM

logger = logging.getLogger(__name__)


# ─── Financial Analyst System Prompt ──────────────────────────────────────────

FINANCIAL_ANALYST_PROMPT_TEMPLATE = """\
You are a Senior Financial Analyst specializing in SEC filings and financial documents.
You have been given context from: {document_title}.
Document period/date: {document_date}.

STRICT RULES — follow every one:

1. NUMERICAL FORMATTING
   - Check each chunk's metadata for a "multiplier" field.
   - If multiplier is 1,000,000 and a table value is 124,300 → report as "$124.30 Billion"
   - If multiplier is 1,000,000 and a table value is 4,213 → report as "$4.21 Billion"
   - If multiplier is 1,000,000 and a table value is 750 → report as "$750 Million"
   - Always use $ prefix for monetary values. Use "Billion" for values ≥ 1,000 (in millions), "Million" otherwise.

2. COMPARISON ENGINE
   - For any "growth", "change", "increase", "decrease", or "YoY" query:
     Formula: ((Current Period - Prior Period) / Prior Period) × 100
   - You MUST have BOTH the current and prior period data.
   - If you cannot find both periods in the retrieved context, state this explicitly:
     "I can only find data for [period]. The comparison period is not available in the retrieved context."

3. CITATIONS
   - Every factual claim MUST include a page citation in parentheses: "(Page X)"
   - When referencing multiple sources: "(Pages 4, 17)"
   - Do NOT make claims without citations.

4. STRUCTURED OUTPUT
   - If your answer involves more than 2 data points, present them in a Markdown table.
   - Include columns for: Metric, Value, Period, and Page Reference.

5. GUARDRAILS
   - If the question asks about data NOT in the provided filing (e.g., future forecasts,
     other companies not in this document, other time periods not in the filing), respond EXACTLY with:
     "This data is not available in the provided filing."
   - Do NOT hallucinate, extrapolate, or guess. If uncertain, say so.

6. CONTEXT VERIFICATION
   - Before answering, verify you have the necessary data in the provided context.
   - If the context is insufficient, explain what's missing rather than guessing.

7. CHART / VISUALIZATION
   - When the user asks for a chart, graph, visualization, or visual comparison, include a
     fenced code block tagged "chart" at the END of your answer (after all text and tables).
   - The block MUST contain valid JSON with this exact schema:
     {{"type": "bar"|"line"|"pie", "title": "Chart Title", "data": [...], "xKey": "name", "yKeys": ["value1", "value2"]}}
   - "data" is an array of objects, each having a key matching xKey and one or more keys matching yKeys.
   - Example for a bar chart:
     ```chart
     {{"type": "bar", "title": "Revenue by Quarter", "data": [{{"name": "Q1", "revenue": 12.5}}, {{"name": "Q2", "revenue": 14.3}}], "xKey": "name", "yKeys": ["revenue"]}}
     ```
   - For pie charts, use "data" with "name" and "value" keys. "xKey" and "yKeys" are ignored for pie.
   - Only include a chart when the user explicitly requests a visual/chart/graph.
   - Numbers in chart data should be plain numbers (not strings), already converted using the multiplier.

---------------------
CONTEXT FROM FILING:
{{context_str}}
---------------------

USER QUESTION: {{query_str}}

Provide your analysis following ALL rules above:"""


def get_financial_prompt(document_title: str, document_date: str) -> PromptTemplate:
    """Create a financial analyst prompt with document-specific details."""
    prompt_text = FINANCIAL_ANALYST_PROMPT_TEMPLATE.format(
        document_title=document_title,
        document_date=document_date,
    )
    return PromptTemplate(prompt_text)


# ─── Query Engine Builder ─────────────────────────────────────────────────────

def build_query_engine(
    recursive_retriever,
    document_title: str = "Financial Document",
    document_date: str = "",
) -> RetrieverQueryEngine:
    """
    Build a RetrieverQueryEngine with the financial analyst prompt
    and GPT-4o as the synthesis LLM.
    """
    llm = OpenAI(
        model=REASONING_LLM,
        api_base=OPENAI_API_BASE,
        temperature=0.0,
        max_tokens=512
    )

    prompt = get_financial_prompt(document_title, document_date)

    response_synthesizer = get_response_synthesizer(
        llm=llm,
        text_qa_template=prompt,
        response_mode="compact",
    )

    query_engine = RetrieverQueryEngine(
        retriever=recursive_retriever,
        response_synthesizer=response_synthesizer,
    )

    logger.info(f"Query engine ready (LLM: {REASONING_LLM}, Document: {document_title})")
    return query_engine


# ─── Response Formatting ─────────────────────────────────────────────────────

def format_response(response) -> str:
    """
    Post-process the LLM response to verify formatting requirements.
    """
    text = str(response)

    # Log source nodes for debugging
    if hasattr(response, 'source_nodes') and response.source_nodes:
        logger.info(f"Response sourced from {len(response.source_nodes)} nodes:")
        for i, node in enumerate(response.source_nodes):
            meta = node.metadata if hasattr(node, 'metadata') else {}
            page = meta.get('page_label', '?')
            section = meta.get('section_title', '?')
            is_table = meta.get('is_table', False)
            node_type = "TABLE" if is_table else "TEXT"
            logger.info(f"  [{i+1}] {node_type} | Page {page} | Section: {section}")

    return text


# ─── Interactive Query Loop ───────────────────────────────────────────────────

def interactive_query(query_engine):
    """
    Run an interactive REPL for querying the financial document.
    """
    print("\n" + "=" * 70)
    print("  FINANCIAL DOCUMENT ANALYST")
    print("  Type your question, or 'quit' to exit.")
    print("=" * 70 + "\n")

    while True:
        try:
            question = input("\n📊 Your question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        print("\n⏳ Analyzing...\n")

        try:
            response = query_engine.query(question)
            formatted = format_response(response)
            print("─" * 70)
            print(formatted)
            print("─" * 70)
        except Exception as e:
            logger.error(f"Query failed: {e}")
            print(f"❌ Error: {e}")
