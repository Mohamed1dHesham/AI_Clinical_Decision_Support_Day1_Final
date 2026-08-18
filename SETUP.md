# Setup — AI Clinical Decision Support Lite

This file is the short operational setup guide. For architecture, project scope, evaluation, safety and detailed usage, see `README.md`.

---

## 1. Open the project

Open PowerShell in the project root:

```powershell
cd AI_Clinical_Decision_Support
```

---

## 2. Create a virtual environment

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the environment's Python directly.

---

## 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Configure Groq

```powershell
Copy-Item .env.example .env
```

Set:

```text
GROQ_API_KEY=your_real_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

Keep `.env` private.

---

## 5. Build the Chroma index

Run this after installation and whenever the PDFs, chunking or metadata logic changes:

```powershell
python -m src.main index
```

The local database is created at:

```text
chroma_db/
```

It is intentionally ignored by Git.

---

## 6. Validate the project

Run:

```powershell
pytest -q
```

Then generate the Day-1 retrieval baseline:

```powershell
python -m src.main evaluate
```

The report is generated at:

```text
outputs/retrieval_baseline.json
```

---

## 7. Start the web application

```powershell
python -m uvicorn src.web:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

---

## 8. Useful CLI commands

### Search

```powershell
python -m src.main search "How is hypertension confirmed using ambulatory blood pressure monitoring?"
```

### Evaluate

```powershell
python -m src.main evaluate
```

### Generate grounded answer

```powershell
python -m src.main answer "What are common side effects of ACE inhibitors?"
```

---

## 9. API health check

With the server running:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

The response includes `index_ready` so you can tell whether the Chroma collection has been built.

---

## 10. API question test

```powershell
$body = @{
  question = "What lifestyle changes can help lower blood pressure?"
  top_k = 4
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/api/ask `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

---

## 11. Rebuild from scratch

If the local index is stale:

```powershell
Remove-Item -Recurse -Force .\chroma_db
Remove-Item -Force .\outputs\retrieval_baseline.json -ErrorAction SilentlyContinue
python -m src.main index
python -m src.main evaluate
```

---

## 12. Common issue: PowerShell activation

If this fails:

```powershell
.\.venv\Scripts\Activate.ps1
```

you can still install and run using:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.main index
.\.venv\Scripts\python.exe -m uvicorn src.web:app --reload
```

---

## 13. Common issue: vector database not ready

If the application reports that Chroma is not ready, run:

```powershell
python -m src.main index
```

Then restart the server if necessary.

---

## 14. Common issue: changed ingestion code

If you modify `src/ingestion.py`, metadata logic, chunking configuration, or the source PDFs, always rebuild:

```powershell
Remove-Item -Recurse -Force .\chroma_db
python -m src.main index
python -m src.main evaluate
```

Never use an old retrieval baseline to represent a newly indexed corpus.
