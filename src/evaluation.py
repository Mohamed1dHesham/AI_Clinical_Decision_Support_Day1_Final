import json
from pathlib import Path
from typing import Dict, List

from src.config import OUTPUT_DIR, TOP_K
from src.vector_store import retrieve

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "evaluation" / "questions.json"


def load_questions() -> List[Dict]:
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def relevance_level(row: Dict, gold: Dict) -> str:
    """Classify evidence without pretending similarity is a clinical confidence score.

    exact: gold document + gold page + gold section
    section: gold document + gold section
    page: gold document + gold page
    none: outside the labeled evidence target
    """
    md = row["metadata"]
    same_doc = md.get("document_id") == gold["document_id"]
    page_match = int(md.get("page_number", -1)) in gold.get("relevant_pages", [])
    section_match = md.get("section") in gold.get("relevant_sections", [])
    if same_doc and page_match and section_match:
        return "exact"
    if same_doc and section_match:
        return "section"
    if same_doc and page_match:
        return "page"
    return "none"


def is_relevant(row: Dict, gold: Dict) -> bool:
    return relevance_level(row, gold) != "none"


def evaluate_k(k: int = TOP_K) -> Dict:
    questions = load_questions()
    rows = []
    precisions = []
    strict_precisions = []
    reciprocal_ranks = []

    for q in questions:
        results = retrieve(q["question"], top_k=k)
        levels = [relevance_level(r, q) for r in results]
        flags = [level != "none" for level in levels]
        strict_flags = [level == "exact" for level in levels]

        precision = sum(flags) / max(len(flags), 1)
        strict_precision = sum(strict_flags) / max(len(strict_flags), 1)
        precisions.append(precision)
        strict_precisions.append(strict_precision)

        rr = 0.0
        for idx, flag in enumerate(flags, 1):
            if flag:
                rr = 1.0 / idx
                break
        reciprocal_ranks.append(rr)

        rows.append({
            "id": q["id"],
            "question": q["question"],
            "precision_at_k": precision,
            "strict_precision_at_k": strict_precision,
            "relevant_in_top_k": sum(flags),
            "results": [
                {
                    "rank": r["rank"],
                    "similarity": r["similarity"],
                    "relevance": level,
                    "relevant": level != "none",
                    "metadata": r["metadata"],
                }
                for r, level in zip(results, levels)
            ],
        })

    return {
        "methodology": {
            "relevant_if": "same document AND (gold page OR gold section)",
            "strict_relevant_if": "same document AND gold page AND gold section",
            "similarity_note": "Similarity is a retrieval ranking signal, not a probability or clinical confidence score.",
        },
        "summary": {
            "question_count": len(questions),
            "k": k,
            "precision_at_k": sum(precisions) / max(len(precisions), 1),
            "strict_precision_at_k": sum(strict_precisions) / max(len(strict_precisions), 1),
            "mrr": sum(reciprocal_ranks) / max(len(reciprocal_ranks), 1),
        },
        "questions": rows,
    }


def save_evaluation(k: int = TOP_K) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = evaluate_k(k)
    path = OUTPUT_DIR / f"retrieval_evaluation_top{k}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
