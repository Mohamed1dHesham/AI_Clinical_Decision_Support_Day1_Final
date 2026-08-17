import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

app = FastAPI(
    title="AI Clinical Decision Support API",
    version="0.2.0",
    description="Day-1/Day-2 retrieval API for the hypertension clinical RAG prototype.",
)

allowed_origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class SearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=4, ge=1, le=10)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 3:
            raise ValueError("Question is too short")
        return value


@app.get("/health")
def health():
    return {"status": "ok", "service": "clinical-rag-retrieval", "scope": "adult-hypertension"}


@app.post("/api/search")
def search(request: SearchRequest):
    try:
        from vector_store import retrieve
        results = retrieve(request.question, request.top_k)
        return {
            "question": request.question,
            "results": results,
            "educational_only": True,
            "scope": "adult-hypertension",
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Retrieval service is unavailable. Build the vector index first.") from exc
