# AI Exam Paper Predictor — Frontend (Phase 05)

Next.js dashboard for the FastAPI backend: subject question banks, probability
dashboard (frequency meters + hot/warm/cold syllabus coverage), and the predicted
paper rendered as a question-paper sheet with red-pen probability stamps.

## Run

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — the backend must be running on port 8000
(`.venv\Scripts\uvicorn app.main:app --reload` in `backend/`).

Point at a different backend with `NEXT_PUBLIC_API_URL` in `.env.local`.

## Pages

| Route | What it shows |
|---|---|
| `/` | Subjects with paper counts; upload the first paper of a new subject |
| `/subjects/[subject]` | Papers on file, run analysis, most-probable-questions table, syllabus coverage, uploads |
| `/subjects/[subject]/predict` | Predict buttons (Gemini-phrased or offline), the model paper sheet, past runs |
