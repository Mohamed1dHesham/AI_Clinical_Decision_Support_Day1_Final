from typing import Dict, List

import chromadb
from chromadb.config import Settings
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.documents import Document

from src.config import COLLECTION_NAME, DB_DIR, EMBEDDING_MODEL


def get_embeddings():
    return FastEmbedEmbeddings(model_name=EMBEDDING_MODEL)


def _get_client():
    return chromadb.PersistentClient(
        path=str(DB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


def build_vector_store(chunks: List[Dict]):
    DB_DIR.mkdir(parents=True, exist_ok=True)
    embeddings = get_embeddings()
    client = _get_client()

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    documents = [
        Document(page_content=x["text"], metadata=x["metadata"])
        for x in chunks
    ]
    texts = [d.page_content for d in documents]
    vectors = embeddings.embed_documents(texts)

    collection.add(
        ids=[x["id"] for x in chunks],
        documents=texts,
        embeddings=vectors,
        metadatas=[x["metadata"] for x in chunks],
    )
    return collection


def open_collection():
    client = _get_client()
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError(
            "The Chroma vector database is not ready. Run `python -m src.main index` first."
        ) from exc


def index_ready() -> bool:
    if not DB_DIR.exists():
        return False
    try:
        collection = _get_client().get_collection(COLLECTION_NAME)
        return collection.count() > 0
    except Exception:
        return False


def retrieve(query: str, top_k: int = 4):
    if not query.strip():
        return []
    if top_k < 1 or top_k > 10:
        raise ValueError("top_k must be between 1 and 10")

    embeddings = get_embeddings()
    collection = open_collection()
    q_vector = embeddings.embed_query(query)
    result = collection.query(
        query_embeddings=[q_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    rows = []
    for i in range(len(result["ids"][0])):
        distance = float(result["distances"][0][i])
        rows.append({
            "rank": i + 1,
            "similarity": 1.0 - distance,
            "distance": distance,
            "text": result["documents"][0][i],
            "metadata": result["metadatas"][0][i],
        })
    return rows
