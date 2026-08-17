import argparse
import sys
from pathlib import Path

# Support both `python src/main.py ...` and `python -m src.main ...`.
# When executed as a file, Python puts `src/` on sys.path instead of the
# project root, so we explicitly add the project root before importing `src`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import CHUNK_OVERLAP_TOKENS, CHUNK_TARGET_TOKENS, EMBEDDING_MODEL, TOP_K, MAX_TOP_K
from src.ingestion import load_documents


def index():
    # Import only when vector functionality is actually needed.
    from src.vector_store import build_vector_store
    chunks = load_documents()
    print(f"[1/3] Parsed + chunked: {len(chunks)} chunks")
    store = build_vector_store(chunks)
    print(f"[2/3] Indexed in Chroma collection: {store.name}")
    print(f"      target_tokens={CHUNK_TARGET_TOKENS}, overlap_tokens={CHUNK_OVERLAP_TOKENS}")
    print(f"      embedding={EMBEDDING_MODEL}")
    return len(chunks)


def search(query: str, top_k: int = TOP_K):
    from src.vector_store import retrieve
    rows = retrieve(query, top_k=top_k)
    print(f"\nQuestion: {query}\n")
    for r in rows:
        m = r["metadata"]
        print(f"Rank {r['rank']} | Page {m['page_number']} | Similarity {r['similarity']:.4f} | {m['chunk_id']}")
        print(f"Document: {m['document_name']}\nSection: {m['section']}\nText: {r['text'][:700]}\n")
    return rows


def evaluate(k: int = TOP_K):
    from src.evaluation import save_evaluation
    path = save_evaluation(k)
    print(f"Saved retrieval evaluation: {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="Clinical RAG Day 1/2 - Hypertension retrieval pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("index", help="Parse PDFs, chunk, embed and build Chroma")
    p_search = sub.add_parser("search", help="Retrieve Top-K evidence")
    p_search.add_argument("question", nargs="+", help="Clinical question")
    p_search.add_argument("--k", type=int, default=TOP_K, choices=range(1, MAX_TOP_K + 1))
    p_eval = sub.add_parser("evaluate", help="Run labeled retrieval evaluation")
    p_eval.add_argument("--k", type=int, default=TOP_K, choices=range(1, MAX_TOP_K + 1))
    p_validate = sub.add_parser("validate", help="Validate PDF parsing/chunking without embeddings")
    args = parser.parse_args()

    try:
        if args.command == "index":
            index()
        elif args.command == "search":
            search(" ".join(args.question), args.k)
        elif args.command == "evaluate":
            evaluate(args.k)
        elif args.command == "validate":
            chunks = load_documents()
            print(f"Validated ingestion successfully: {len(chunks)} chunks")
            bad = [c for c in chunks if not c["metadata"].get("section")]
            print(f"Chunks with missing section: {len(bad)}")
            print(f"Chunk IDs unique: {len({c['id'] for c in chunks}) == len(chunks)}")
            if bad:
                raise ValueError("Validation failed: one or more chunks have no section metadata.")
    except ImportError as exc:
        print("Missing dependency. Run: pip install -r requirements.txt", file=sys.stderr)
        print(exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
