import argparse
import json
import sys
from pathlib import Path

from src.config import (
    OUTPUT_DIR,
    TOP_K,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL,
    CLINICAL_TEST_QUESTIONS_PATH,
    CLINICAL_SCOPE,
)
from src.ingestion import load_documents
from src.vector_store import build_vector_store, retrieve
from src.llm import generate_grounded_answer


def load_test_questions():
    try:
        with CLINICAL_TEST_QUESTIONS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid evaluation JSON at {CLINICAL_TEST_QUESTIONS_PATH}: {exc}"
        ) from exc

    if not isinstance(data, list) or not data:
        raise ValueError("Clinical evaluation set must be a non-empty JSON list.")

    for item in data:
        if not item.get("id") or not item.get("question"):
            raise ValueError("Each evaluation item requires id and question fields.")

    return data


def index():
    chunks = load_documents()
    print(f"[1/3] Parsed + chunked: {len(chunks)} chunks")
    store = build_vector_store(chunks)
    print(f"[2/3] Indexed in Chroma collection: {store.name}")
    print(f"      scope={CLINICAL_SCOPE}")
    print(f"      chunk_size={CHUNK_SIZE} characters, overlap={CHUNK_OVERLAP} characters")
    print(f"      embedding={EMBEDDING_MODEL}")
    print("[3/3] Index ready")
    return len(chunks)


def search(query: str, top_k: int = TOP_K):
    rows = retrieve(query, top_k=top_k)
    print(f"\nQuestion: {query}\n")
    for r in rows:
        m = r["metadata"]
        print(
            f"Rank {r['rank']} | Page {m['page_number']} | "
            f"Similarity {r['similarity']:.4f} | {m['chunk_id']}"
        )
        print(f"Document: {m['document_name']}")
        print(f"Section: {m['section']}")
        print(f"Text: {r['text'][:700]}\n")
    return rows


def evaluate():
    OUTPUT_DIR.mkdir(exist_ok=True)
    questions = load_test_questions()
    report = []
    source_hits = 0
    section_hits = 0

    for item in questions:
        rows = retrieve(item["question"], top_k=TOP_K)
        expected_sources = set(item.get("expected_sources", []))
        expected_sections = set(item.get("expected_sections", []))

        retrieved_sources = {r["metadata"].get("document_id") for r in rows}
        retrieved_sections = {r["metadata"].get("section") for r in rows}

        source_hit = bool(expected_sources & retrieved_sources) if expected_sources else None
        section_hit = bool(expected_sections & retrieved_sections) if expected_sections else None

        if source_hit:
            source_hits += 1
        if section_hit:
            section_hits += 1

        report.append({
            "question_id": item["id"],
            "question": item["question"],
            "topic": item.get("topic"),
            "expected_sources": item.get("expected_sources", []),
            "expected_sections": item.get("expected_sections", []),
            "expected_evidence": item.get("expected_evidence", []),
            "source_hit_at_k": source_hit,
            "section_hit_at_k": section_hit,
            "results": [
                {
                    "rank": r["rank"],
                    "similarity": r["similarity"],
                    "metadata": r["metadata"],
                }
                for r in rows
            ],
        })

    summary = {
        "questions": len(questions),
        "top_k": TOP_K,
        "source_hit_rate": source_hits / len(questions),
        "section_hit_rate": section_hits / len(questions),
    }

    payload = {"summary": summary, "questions": report}
    path = OUTPUT_DIR / "retrieval_baseline.json"
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved baseline retrieval report: {path}")
    print(f"Source hit@{TOP_K}: {summary['source_hit_rate']:.1%}")
    print(f"Section hit@{TOP_K}: {summary['section_hit_rate']:.1%}")


def main():
    parser = argparse.ArgumentParser(
        description="Clinical RAG Day 1 - Adult Hypertension retrieval pipeline"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("index", help="Parse PDFs, chunk, embed and build Chroma")

    p_search = sub.add_parser("search", help="Retrieve Top-K evidence")
    p_search.add_argument("question", nargs="+", help="Clinical question")

    sub.add_parser("evaluate", help="Run the clinical evaluation set")

    p_answer = sub.add_parser("answer", help="Retrieve evidence and generate a grounded Groq answer")
    p_answer.add_argument("question", nargs="+", help="Clinical question")

    args = parser.parse_args()

    try:
        if args.command == "index":
            index()
        elif args.command == "search":
            search(" ".join(args.question))
        elif args.command == "evaluate":
            evaluate()
        elif args.command == "answer":
            question = " ".join(args.question)
            rows = search(question)
            print("\nGrounded answer:\n")
            print(generate_grounded_answer(question, rows))
    except (ImportError, FileNotFoundError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        if isinstance(exc, ImportError):
            print("Run: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
