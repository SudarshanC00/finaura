"""
Financial RAG Pipeline — CLI Entry Point.

Commands:
  python main.py ingest --pdf <path>     Parse PDF and build vector index
  python main.py query                   Interactive query REPL
  python main.py query --single "..."    One-shot query
"""

import argparse
import logging
import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import OPENAI_API_KEY


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)


def cmd_ingest(args):
    """Run the ingestion pipeline."""
    from indexer import create_index
    from ingest import ingest_pdf

    pdf_path = args.pdf
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)

    print(f"📄 Ingesting: {pdf_path}")
    print("   This may take a few minutes for table summarization...\n")

    # Step 1: Parse PDF → nodes
    nodes = ingest_pdf(pdf_path)
    if not nodes:
        print("❌ No content extracted from PDF.")
        sys.exit(1)

    table_nodes = [n for n in nodes if n.metadata.get("is_table")]
    text_nodes = [n for n in nodes if not n.metadata.get("is_table")]
    print(f"\n✅ Parsed: {len(table_nodes)} table nodes, {len(text_nodes)} text nodes")

    # Step 2: Build Qdrant index
    print("\n📦 Building vector index...")
    create_index(nodes)
    print(f"✅ Index created successfully! ({len(nodes)} total nodes)")
    print("   Stored at: ./storage/")


def cmd_query(args):
    """Run queries against the index."""
    from indexer import build_recursive_retriever, load_or_create_index
    from query_engine import build_query_engine, format_response, interactive_query

    print("🔍 Loading index...")
    index = load_or_create_index()

    print("🔗 Building recursive retriever...")
    retriever = build_recursive_retriever(index)

    print("🧠 Initializing query engine...")
    engine = build_query_engine(retriever)

    if args.single:
        # One-shot mode
        print(f"\n📊 Query: {args.single}\n")
        print("⏳ Analyzing...\n")
        response = engine.query(args.single)
        formatted = format_response(response)
        print("─" * 70)
        print(formatted)
        print("─" * 70)
    else:
        # Interactive REPL
        interactive_query(engine)


def main():
    parser = argparse.ArgumentParser(
        description="Financial RAG Pipeline for Apple Q1 2026 10-Q",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python main.py ingest --pdf data/apple_10q_q1_2026.pdf
  python main.py query
  python main.py query --single "What was Apple's total net sales for Q1 2026?"
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── ingest command ────────────────────────────────────────────────────
    ingest_parser = subparsers.add_parser("ingest", help="Parse PDF and build vector index")
    ingest_parser.add_argument(
        "--pdf",
        required=True,
        help="Path to the Apple 10-Q PDF file",
    )

    # ── query command ─────────────────────────────────────────────────────
    query_parser = subparsers.add_parser("query", help="Query the 10-Q filing")
    query_parser.add_argument(
        "--single",
        type=str,
        default=None,
        help="Single query (non-interactive mode)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Validate API key
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not set. Add it to your .env file or environment.")
        sys.exit(1)

    setup_logging(args.verbose)

    if args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "query":
        cmd_query(args)


if __name__ == "__main__":
    main()
