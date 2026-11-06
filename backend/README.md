# AI Exam Paper Predictor — Backend (Phases 02–04)

Full prediction pipeline: upload past exam papers (PDF/image) → text extraction
(PyMuPDF text layer, Tesseract OCR fallback) → Gemini structured parsing → storage →
embeddings + semantic dedup → frequency/recency statistics → syllabus coverage (Mode 2)
→ pattern engine (rotation/frequency/surprise rules) → mock paper with probabilities,
optionally phrased by Gemini.

## Prerequisites

- **Python 3.12**
- **Tesseract OCR** — only needed for scanned PDFs/images (digital PDFs are read
  directly). Installed on this machine at `C:\Program Files\Tesseract-OCR`.
- **Gemini API key** — only needed for parsing uploads and Gemini-phrased
  generation; see [Running without a Gemini key](#running-without-a-gemini-key)
  for what works offline. Get a free key at https://aistudio.google.com/apikey.

## First-time setup

Run once, from the `backend/` directory:

```powershell
cd backend
python -m venv .venv                                  # create the virtualenv
.venv\Scripts\pip install -r requirements.txt         # install dependencies
copy .env.example .env                                # create local config
```

Then open `.env` and set `GEMINI_API_KEY=<your key>`. All other settings have
working defaults (SQLite database, upload storage under `./storage/papers`);
see `.env.example` for what each one does.

## Run

From the `backend/` directory:

```powershell
.venv\Scripts\uvicorn app.main:app --reload
```

- Server: http://127.0.0.1:8000
- Interactive API docs (Swagger UI): http://127.0.0.1:8000/docs
- `--reload` restarts the server on code changes (development mode; drop it in
  production).

The SQLite database (`exam_analyzer.db`) and its tables are created
automatically on startup — no migration step needed.

Verify it's up:

```powershell
curl.exe http://127.0.0.1:8000/health   # → {"status":"ok"}
```

To use a different port or accept external connections:

```powershell
.venv\Scripts\uvicorn app.main:app --reload --port 8080
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Note: the frontend expects the backend on port 8000, and CORS is configured
for the frontend at `http://localhost:3000` — if you change either port,
update `frontend`'s API base URL and/or `allow_origins` in `app/main.py`.

### Running without a Gemini key

With no `GEMINI_API_KEY` set, the server still starts and everything that
doesn't call Gemini works: listing/deleting papers, frequency and coverage
analysis over already-parsed data, and offline prediction via
`POST /predict/{subject}?generate=false` (uses historical phrasings instead of
Gemini). Uploading new papers/syllabi (Gemini parsing), `POST /analysis/{subject}/run`
(embeddings), and default generation (`generate=true`) require the key.

### Stopping

`Ctrl+C` in the terminal running uvicorn.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/papers` | Upload a paper (multipart: `file`, `subject`, `year`, optional `exam_session`, `examiner`) — extracts, parses, stores |
| GET | `/papers` | List papers (optional `?subject=` filter) |
| GET | `/papers/{id}` | One paper with its parsed questions |
| DELETE | `/papers/{id}` | Remove a paper and its questions |
| POST | `/syllabus` | Upload the official syllabus (multipart: `file`, `subject`) — parses topics (Mode 2) |
| GET | `/syllabus/{subject}` | Stored syllabus topics |
| POST | `/analysis/{subject}/run` | Embed → dedup → map to topics; run after uploading papers |
| GET | `/analysis/{subject}/frequency` | Ranked question groups with `p_base` and recency-weighted `p_weighted` |
| GET | `/analysis/{subject}/coverage` | Hot/warm/cold syllabus coverage (needs syllabus) |
| POST | `/predict/{subject}` | Generate the mock paper (`?generate=false` = offline, historical phrasings; default `true` = Gemini-phrased) |
| GET | `/predictions/{subject}` | Past prediction runs |
| GET | `/predictions/run/{run_id}` | One stored run with items |
| GET | `/health` | Liveness check |

Example upload:

```powershell
curl.exe -F "file=@cs301_may_2025.pdf" -F "subject=CS301" -F "year=2025" -F "exam_session=May" http://127.0.0.1:8000/papers
```

## Notes

- DB defaults to SQLite (`exam_analyzer.db`). Phase 03 requires switching `DATABASE_URL`
  to PostgreSQL + pgvector (uncomment `psycopg2-binary` in requirements.txt).
