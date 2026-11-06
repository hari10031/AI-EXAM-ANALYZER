# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository State

Design docs live in `Implementations/`; code lives in `backend/` (FastAPI, Python 3.12) and `frontend/` (Next.js 16, TypeScript). All five MVP phases are built: ingestion/parsing, analysis engine, pattern engine + generation, and the web UI. `POST /predict/{subject}?generate=false` works fully offline. Live Gemini calls are unverified — no `GEMINI_API_KEY` on this machine yet. Not a git repository.

## Commands

Backend, from `backend/` (venv at `backend/.venv`):

```powershell
python -m venv .venv                                  # one-time setup
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env                                # then add GEMINI_API_KEY
.venv\Scripts\uvicorn app.main:app --reload           # run server → http://127.0.0.1:8000/docs
```

Frontend, from `frontend/` (needs the backend on port 8000; CORS is preconfigured for port 3000):

```powershell
npm install                                           # one-time setup
npm run dev                                           # → http://localhost:3000
npm run build                                         # production build / type check
```

There is no test suite yet. Config comes from `backend/.env` (see `.env.example`): DB defaults to SQLite; embeddings are stored as normalized JSON arrays with numpy cosine similarity (pgvector is the documented scale-up path — Postgres is not installed on this machine). Tesseract is installed at `C:\Program Files\Tesseract-OCR` for the OCR fallback path.

## Project: AI Exam Paper Predictor

A system that ingests historical exam papers (5–10 years), detects question/topic patterns, and generates a mock future exam paper with a "Probability of Appearance" attached to each question and sub-question (2a, 2b, etc.).

### Planned Architecture (from Implmentation-01.md)

RAG + statistical analysis + LLM reasoning — **not** model training from scratch. The core accuracy principle: probabilities are computed with strict Python math (frequency counts over N years), and the LLM only formats/phrases questions based on those precomputed numbers. Never let the LLM guess probabilities.

Pipeline:
1. **Ingestion/OCR** — Upload PDFs/images of past papers; OCR extracts text; an LLM parses it into structured JSON (Year, Question Number, Part a/b, Marks, Question Text).
2. **Dual-track analysis** — Track A: statistical frequency of exact + semantic question matches. Track B: embed questions and map them to syllabus topics (when a syllabus is provided).
3. **Pattern logic engine** — rules-based (e.g., topic appeared 4/5 years → 80% probability; enforce recurring question structures like "2a theory / 2b numerical"; flag heavily-weighted-but-untested topics as "High Probability Surprise").
4. **Generative output** — pass statistical data, structural rules, and syllabus constraints to an LLM with a strict prompt to produce the formatted mock paper with confidence percentages.

Two operating modes:
- **Mode 1 (Pattern Only)**: predictions from past papers alone.
- **Mode 2 (Syllabus-Constrained)**: user uploads the syllabus; questions are mapped to topics, untouched syllabus areas are identified, and generation balances historical patterns with untested topics.

Other accuracy requirements: semantic deduplication of reworded questions via embedding cosine similarity; optional examiner profiling as prediction metadata.

### Planned Tech Stack

Backend: Python (FastAPI) · Frontend: Next.js · Database: PostgreSQL + pgvector (question embeddings for semantic search) · OCR: Tesseract (MVP) with Google Document AI as upgrade path · Data processing: Pandas, spaCy. All AI calls are standardized on **Gemini** (decided 2026-07-04): Gemini 3.1 Pro for generation, Gemini 3.5 Flash for high-volume parsing, gemini-embedding-2 for embeddings. LangChain is optional orchestration only — not required for the MVP.

## Workflow Conventions

- Each implementation phase gets its own numbered doc in `Implementations/` following the existing filename pattern: `Implmentation-01.md`, `Implmentation-02.md`, and so on (note the existing spelling "Implmentation" — keep filenames consistent). The phase roadmap (what goes in 02–05) is defined in `Implmentation-01.md` §8.
- When adding a new phase doc, also update the History/Changelog table at the bottom of `Implmentation-01.md` and update Claude's local memory with the project's current state.
