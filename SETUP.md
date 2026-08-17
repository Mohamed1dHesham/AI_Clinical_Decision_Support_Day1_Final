# Setup — AI Clinical Decision Support

## 1. Backend / RAG environment (Windows PowerShell)

```powershell
cd AI_Clinical_Decision_Support
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. Validate Day-1 ingestion without embeddings

```powershell
python src\main.py validate
python -m pytest -q
```

This checks PDF parsing, section detection, chunk creation and metadata without requiring Chroma or an embedding model.

## 3. Build the vector database

```powershell
python src\main.py index
```

The first embedding run may download `BAAI/bge-small-en-v1.5`.

## 4. Test retrieval

```powershell
python src\main.py search "How is hypertension confirmed using ambulatory blood pressure monitoring?" --k 4
```

## 5. Run the labeled evaluation

```powershell
python src\main.py evaluate --k 3
python src\main.py evaluate --k 4
python src\main.py evaluate --k 5
```

Compare Precision@K and MRR across the three runs before changing the retrieval configuration.

## 6. Run the FastAPI backend

```powershell
uvicorn backend.app.main:app --reload --port 8000
```

Health check:

```text
http://localhost:8000/health
```

## 7. Run the Next.js UI

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

The UI currently demonstrates the retrieval layer only. It intentionally does not generate medical answers yet; generation, citations and safety are later-stage tasks.

## 8. Day-1 validation notes

After changing the corpus, parsing rules, chunking settings, or embedding collection version, rebuild the index with:

```powershell
python src\main.py index
```

The current collection name is versioned for this Day-1 baseline, so old collections are not silently reused.

The evaluation JSON contains per-question relevance labels (`exact`, `section`, `page`, `none`) so retrieval failures can be inspected before optimizing the retriever.
