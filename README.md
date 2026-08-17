# AI Clinical Decision Support — Hypertension RAG

## Current milestone: Day 1 foundation + Day 2 retrieval/UI baseline

This project implements the retrieval foundation for a clinical RAG prototype using the two approved NICE hypertension PDFs supplied for the hackathon:

1. *Hypertension in adults: diagnosis and management (NG136)*
2. *How do I control my blood pressure? Lifestyle options and choice of medicines*

The current pipeline is:

```text
PDF → Parse → Clean → Section-aware Chunk → Embed → Chroma
                                             ↓
Question → Query Embedding → Cosine Similarity → Top-K Evidence
```

The hackathon Day-1 requirement is to define the clinical scope and build a reliable document-ingestion pipeline: select official PDFs, verify accessibility/legal usability, parse, section-aware chunk, embed, index, and preserve document/section/page metadata. The supplied Day-1 material also states that the final system is educational only and must not diagnose, prescribe, or replace a qualified clinician. 

## What is implemented

- Page-by-page PDF extraction with page numbers preserved
- Document-specific section detection for both PDFs
- Noise/header/footer cleanup
- Approximate token-oriented chunking with sentence-aware boundaries
- Stable chunk IDs
- Metadata: document ID/name, source, version, section, page, chunk ID, token count
- `BAAI/bge-small-en-v1.5` embeddings through FastEmbed
- Chroma persistent vector database using cosine distance
- Top-K retrieval with transparent evidence metadata
- 20-question labeled retrieval benchmark with Precision@K and MRR
- FastAPI retrieval endpoint with request validation and configurable CORS
- Minimal Next.js evidence-search UI
- Day-1 ingestion unit tests

## Day-1/Day-2 boundary

The current web application is intentionally a retrieval/evidence viewer. It does not generate clinical advice yet. Generation, structured citations, safety guardrails, unsupported-claim checking, and the final UI will be developed in later milestones.

## Safety boundary

Educational use only. The prototype must not diagnose, prescribe, select individualized treatment, or recommend personalized drug doses. Questions outside the approved evidence scope should not be answered as if supported by the corpus.

## Recommended workflow

```powershell
python src\main.py validate
python -m pytest -q
python src\main.py index
python src\main.py search "How is hypertension confirmed using ambulatory blood pressure monitoring?" --k 4
python src\main.py evaluate --k 3
python src\main.py evaluate --k 4
python src\main.py evaluate --k 5
```

Then run the backend and frontend using `SETUP.md`.

## Validation status

The Day-1 validation suite now checks:

- unique stable chunk IDs
- required document/section/page metadata
- no ambiguous `General` section labels
- prevention of known false section detections
- reconstruction of wrapped NG136 headings
- corpus presence for both approved documents

The retrieval evaluation also reports both the primary labeled Precision@K methodology (`same document AND gold page OR gold section`) and a stricter exact page+section metric. Similarity is explicitly treated as a ranking signal, not a probability or clinical confidence score.
