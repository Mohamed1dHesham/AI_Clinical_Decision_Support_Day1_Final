from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_DIR = ROOT / "chroma_db"
OUTPUT_DIR = ROOT / "outputs"

# Day 2 baseline: token-oriented targets, with sentence-aware boundaries.
CHUNK_TARGET_TOKENS = 550
CHUNK_OVERLAP_TOKENS = 80
TOP_K = 4
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
COLLECTION_NAME = "hypertension_guidelines_day1_v3"
MAX_QUERY_LENGTH = 1000
MAX_TOP_K = 10
MIN_QUERY_LENGTH = 3

DOCUMENTS = [
    {
        "path": DATA_DIR / "hypertension_nice_ng136.pdf",
        "document_id": "HTN-NG136",
        "title": "Hypertension in adults: diagnosis and management (NG136)",
        "source": "NICE",
        "version": "Published 28 August 2019; last updated 26 February 2026",
    },
    {
        "path": DATA_DIR / "hypertension_patient_decision_aid.pdf",
        "document_id": "HTN-PDA-2019",
        "title": "How do I control my blood pressure? Lifestyle options and choice of medicines",
        "source": "NICE",
        "version": "Last updated August 2019",
    },
]

PDA_HEADINGS = {
    "How do I control my blood pressure?",
    "What are my options?",
    "What does this involve?",
    "Advantages",
    "Disadvantages",
    "What are the types of medicine and what are they called?",
    "What are some of the common side effects?",
    "What are some of the common side effects? (Continued.)",
    "Will I need blood tests?",
    "What else do I need to think about?",
    "How do I control my blood pressure? Lifestyle options and choice of medicines",
}
