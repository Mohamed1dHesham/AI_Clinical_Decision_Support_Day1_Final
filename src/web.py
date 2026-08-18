from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import CLINICAL_SCOPE, TOP_K
from src.vector_store import index_ready
from src.llm import GROQ_MODEL, generate_grounded_answer
from src.vector_store import retrieve

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "web"

app = FastAPI(
    title="AI Clinical Decision Support Lite",
    description="Educational hypertension RAG interface",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=TOP_K, ge=1, le=10)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> Dict[str, Any]:
    ready = index_ready()
    return {
        "status": "ok" if ready else "degraded",
        "scope": CLINICAL_SCOPE,
        "model": GROQ_MODEL,
        "index_ready": ready,
    }


@app.post("/api/ask")
def ask(request: AskRequest) -> Dict[str, Any]:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        rows = retrieve(question, top_k=request.top_k)
        answer = generate_grounded_answer(question, rows)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"The request could not be completed: {exc}",
        ) from exc

    evidence = []
    for row in rows:
        metadata = row["metadata"]
        evidence.append(
            {
                "rank": row["rank"],
                "similarity": round(row["similarity"], 4),
                "text": row["text"],
                "document_name": metadata.get("document_name"),
                "section": metadata.get("section"),
                "page_number": metadata.get("page_number"),
                "chunk_id": metadata.get("chunk_id"),
                "source": metadata.get("source"),
                "source_url": metadata.get("source_url"),
                "version": metadata.get("version"),
            }
        )

    return {
        "question": question,
        "answer": answer,
        "scope": CLINICAL_SCOPE,
        "model": GROQ_MODEL,
        "evidence": evidence,
    }
