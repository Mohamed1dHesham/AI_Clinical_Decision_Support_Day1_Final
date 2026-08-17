from typing import Dict, List

import chromadb
from chromadb.config import Settings
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

from src.config import COLLECTION_NAME, DB_DIR, EMBEDDING_MODEL, MAX_TOP_K, MIN_QUERY_LENGTH, MAX_QUERY_LENGTH


def get_embeddings():
    return FastEmbedEmbeddings(model_name=EMBEDDING_MODEL)


def _client():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(DB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


def build_vector_store(chunks: List[Dict], collection_name: str = COLLECTION_NAME):
    """Build a fresh versioned collection from the current corpus."""
    client = _client()
    embeddings = get_embeddings()

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    texts = [x["text"] for x in chunks]
    vectors = embeddings.embed_documents(texts)
    collection.add(
        ids=[x["id"] for x in chunks],
        documents=texts,
        embeddings=vectors,
        metadatas=[x["metadata"] for x in chunks],
    )
    return collection


def open_collection(collection_name: str = COLLECTION_NAME):
    return _client().get_collection(collection_name)


def retrieve(query: str, top_k: int = 4, collection_name: str = COLLECTION_NAME):
    query = " ".join(query.split())
    if not query or len(query) < MIN_QUERY_LENGTH:
        raise ValueError(f"Query must contain at least {MIN_QUERY_LENGTH} characters.")
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError(f"Query must not exceed {MAX_QUERY_LENGTH} characters.")
    if not 1 <= top_k <= MAX_TOP_K:
        raise ValueError(f"top_k must be between 1 and {MAX_TOP_K}.")

    collection = open_collection(collection_name)
    embeddings = get_embeddings()
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
            "similarity": max(0.0, 1.0 - distance),
            "distance": distance,
            "text": result["documents"][0][i],
            "metadata": result["metadatas"][0][i],
        })
    return rows
