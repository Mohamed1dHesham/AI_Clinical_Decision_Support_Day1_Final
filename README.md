# AI Clinical Decision Support Lite
## Adult Hypertension — Evidence-Grounded Clinical RAG

A hackathon prototype for retrieving evidence from two approved NICE adult-hypertension documents and generating a grounded educational answer from the retrieved evidence.

> **Educational prototype only.** This system is not a diagnostic tool, prescription engine, emergency triage service, or replacement for qualified clinical judgment.

---

## 1. Project Scope

### Clinical domain

**Adult Hypertension**

### Knowledge-base sources

1. **NICE NG136 — Hypertension in adults: diagnosis and management**
2. **NICE Patient Decision Aid — How do I control my blood pressure? Lifestyle options and choice of medicines**

The first source is the main clinician-oriented guideline. The second provides patient-oriented decision-support information about lifestyle choices, medicines, side effects and monitoring.

The Day-1 presentation uses skin cancer / melanoma as a teaching example. That is **not** the clinical scope of this implementation.

---

## 2. What the System Does

```text
Approved NICE PDFs
        ↓
PDF Parsing
        ↓
Text Cleaning
        ↓
Document-Aware Section Detection
        ↓
850-character Chunks + 150-character Overlap
        ↓
BGE-small Embeddings
        ↓
Chroma Vector Database
        ↓
Query Embedding
        ↓
Cosine Similarity Retrieval
        ↓
Top-K Evidence
        ↓
Groq Grounded Answer
        ↓
Web UI + Evidence Panel
```

The system is intentionally restricted to the supplied hypertension documents.

---

## 3. Key Day-1 Design Decisions

### Current UI is the canonical UI

The project keeps the existing lightweight HTML/CSS/JavaScript Day-1 interface.

There is **no requirement to migrate the frontend to Next.js** merely for framework consistency.

Current structure:

```text
web/
├── index.html
├── app.js
└── styles.css
```

Backend:

```text
src/web.py
```

The UI is designed around transparent retrieval rather than framework complexity.

### Section metadata is document-aware

The ingestion pipeline does not use a broad generic heading regex anymore.

The two approved PDFs have different layouts, including tables and wrapped headings. The parser therefore uses document-specific approved heading sets and only accepts exact heading matches, including safe handling for headings split across PDF extraction lines.

This prevents recommendation sentences and table fragments from becoming fake sections.

### Day-1 chunking remains a baseline

The current baseline is:

```text
CHUNK_SIZE = 850 characters
CHUNK_OVERLAP = 150 characters
```

Token-based chunk-size experiments belong to Day 2.

---

## 4. Repository Structure

```text
AI_Clinical_Decision_Support/
│
├── README.md
├── SETUP.md
├── clinical_scope.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── data/
│   ├── hypertension_nice_ng136.pdf
│   ├── hypertension_patient_decision_aid.pdf
│   └── clinical_test_questions.json
│
├── outputs/
│   └── retrieval_baseline.json        # generated after evaluation
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── ingestion.py
│   ├── vector_store.py
│   ├── llm.py
│   ├── main.py
│   └── web.py
│
├── tests/
│   ├── test_ingestion.py
│   └── test_evaluation_data.py
│
└── web/
    ├── index.html
    ├── app.js
    └── styles.css
```

The local `chroma_db/` directory is generated during indexing and is intentionally ignored by Git.

---

## 5. Requirements

Recommended:

- Python 3.10+
- Windows PowerShell, macOS Terminal, or Linux shell
- Internet access during dependency/model setup
- A Groq API key for answer generation

The embedding model is downloaded by FastEmbed on first use, so the first indexing run may take longer than subsequent runs.

---

# 6. Installation — Windows PowerShell

Open PowerShell in the project root.

### Create a virtual environment

```powershell
python -m venv .venv
```

### Activate it

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, you can run the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Otherwise:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

# 7. Configure Groq

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

Open `.env` and set:

```text
GROQ_API_KEY=your_real_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

Never commit `.env` to Git.

---

# 8. Build the Vector Database

The ZIP does not need to contain a generated Chroma database.

Build it locally from the supplied PDFs:

```powershell
python -m src.main index
```

Expected output is similar to:

```text
[1/3] Parsed + chunked: ... chunks
[2/3] Indexed in Chroma collection: hypertension_guidelines
      scope=Adult Hypertension
      chunk_size=850 characters, overlap=150 characters
      embedding=BAAI/bge-small-en-v1.5
[3/3] Index ready
```

The exact chunk count can change if the source PDFs or parsing behavior changes.

---

# 9. Run the Retrieval Evaluation

Validate the evaluation dataset first:

```powershell
python -m pytest -q
```

Then run:

```powershell
python -m src.main evaluate
```

The generated report is:

```text
outputs/retrieval_baseline.json
```

The report contains:

- question ID
- question
- topic
- expected source(s)
- expected section(s)
- source hit at K
- section hit at K
- retrieved metadata
- similarity scores
- summary hit rates

The evaluation is a Day-1 baseline, not the final retrieval-quality claim. Day 2 is responsible for optimization and broader evaluation.

---

# 10. Search from the CLI

Retrieve Top-K evidence for a question:

```powershell
python -m src.main search "How is hypertension confirmed using ambulatory blood pressure monitoring?"
```

Another example:

```powershell
python -m src.main search "What lifestyle changes can help lower blood pressure?"
```

---

# 11. Generate a Grounded Answer from the CLI

After configuring `GROQ_API_KEY`:

```powershell
python -m src.main answer "What are common side effects of ACE inhibitors?"
```

The LLM receives the retrieved evidence together with its source metadata.

The system prompt instructs the model to:

- use only retrieved evidence
- avoid unsupported medical claims
- avoid invented citations
- say when evidence is insufficient
- remain educational rather than diagnostic or prescriptive

---

# 12. Start the Web Application

Run:

```powershell
python -m uvicorn src.web:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

The UI provides:

- clinical question input
- example questions
- grounded answer
- retrieved evidence
- rank
- similarity
- document
- section
- page
- chunk ID
- source
- version
- backend health status

---

# 13. Backend API

## Health Check

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Example response:

```json
{
  "status": "ok",
  "scope": "Adult Hypertension",
  "model": "llama-3.3-70b-versatile",
  "index_ready": true
}
```

If the vector database has not been built yet, `index_ready` will be `false` and the status will be `degraded`.

## Ask a Question

PowerShell:

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

The endpoint validates the question length and Top-K range before running retrieval.

---

# 14. Rebuild the Vector Database

Whenever the ingestion logic, metadata logic, chunking logic, or source PDFs change, rebuild the vector database.

PowerShell:

```powershell
Remove-Item -Recurse -Force .\chroma_db
python -m src.main index
```

Then regenerate the evaluation baseline:

```powershell
python -m src.main evaluate
```

Do not treat an old `retrieval_baseline.json` as valid after changing the indexed corpus.

---

# 15. Testing

Run all tests:

```powershell
pytest -q
```

The current tests verify:

- chunks are produced
- required metadata exists
- page numbers are integers
- chunk IDs match stored IDs
- recommendation sentences are not used as sections
- patient-decision-aid table fragments are not used as sections
- expected patient decision-aid headings are detected
- the Day-1 evaluation JSON is valid and contains the expected metadata fields

---

# 16. Day-1 Evaluation Questions

The project contains eight baseline questions covering:

1. ABPM diagnosis
2. HBPM diagnosis
3. target-organ-damage investigations
4. lifestyle interventions
5. ACE-inhibitor side effects
6. blood-test / monitoring information
7. medication options
8. severe hypertension / 180/120 mmHg or higher

Day 2 should expand the evaluation set toward approximately 15–20 labeled clinical questions and compare retrieval strategies, Top-K values and chunk sizes.

---

# 17. Clinical Safety Boundary

The application is an educational clinical RAG prototype.

It must not be presented as:

- a doctor
- a diagnostic system
- a prescription system
- an individualized treatment selector
- an emergency triage replacement
- a replacement for professional clinical judgment

The knowledge base is intentionally narrow.

Questions requiring evidence outside the two indexed documents should not be answered using unsupported model knowledge.

---

# 18. Source / Legal Checkpoint

The supplied documents identify NICE as the source.

The hackathon documentation requires the team to verify public accessibility, legal/reuse status and mentor scope approval.

The code does not independently establish legal permission to reuse the source documents.

Current documentation status:

```text
Mentor scope approval: PENDING
AI/source reuse confirmation: PENDING
```

Do not change these statuses until the team has the required approval/confirmation.

---

# 19. Day-1 Architecture Status

The Day-1 foundation is:

```text
Clinical PDFs
    ↓
Document-Aware Ingestion
    ↓
Section-Aware Chunks
    ↓
Embeddings
    ↓
Chroma
    ↓
Top-K Retrieval
    ↓
Evidence Panel
    ↓
Grounded LLM Answer
```

The current web UI remains the canonical UI foundation for Days 1–5.

The RAG architecture is not being rewritten merely to introduce a different frontend framework.

---

# 20. Known Day-2 Work

The following are intentionally not presented as Day-1 finished features:

- token-based chunk-size experiments
- Top-3 / Top-5 / Top-10 comparison
- BM25 / hybrid retrieval
- reranking
- larger 15–20 question benchmark
- advanced citation validation
- unsupported-claim detection
- full input-risk classification
- retrieval confidence thresholding
- final production-grade safety layer

These belong to the later hackathon stages described in the project documentation.

---

# 21. Quick Start — Copy/Paste

```powershell
# 1. Create environment
python -m venv .venv

# 2. Activate
.\.venv\Scripts\Activate.ps1

# 3. Install
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure Groq
Copy-Item .env.example .env
# Edit .env and add GROQ_API_KEY

# 5. Build vector database
python -m src.main index

# 6. Run tests
pytest -q

# 7. Generate retrieval baseline
python -m src.main evaluate

# 8. Start web app
python -m uvicorn src.web:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

---

# 22. Project Principle

The project is not trying to build a chatbot that simply "knows medicine."

The goal is to build a system that can show:

```text
Where did this information come from?
        ↓
Which document?
        ↓
Which section?
        ↓
Which page?
        ↓
Which retrieved chunk?
```

The system should prefer transparent, evidence-grounded behavior over fluent unsupported answers.
