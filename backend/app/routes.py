import re
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from . import models, schemas
from .config import get_settings
from .db import get_db
from .ocr import ExtractionError, extract_text
from .parser import ParserError, parse_questions

router = APIRouter(prefix="/papers", tags=["papers"])


def _safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


@router.post("", response_model=schemas.PaperWithQuestions, status_code=201)
async def upload_paper(
    file: UploadFile,
    subject: str = Form(...),
    year: int = Form(...),
    exam_session: str | None = Form(None),
    examiner: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Upload one past paper (PDF/image): extract text, parse into questions via
    Gemini, store paper + questions."""
    settings = get_settings()
    storage = Path(settings.storage_dir)
    storage.mkdir(parents=True, exist_ok=True)

    filename = _safe_filename(file.filename or "paper.pdf")
    dest = storage / f"{subject}_{year}_{filename}"
    dest.write_bytes(await file.read())

    try:
        raw_text = extract_text(dest)
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        parsed = parse_questions(raw_text)
    except ParserError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    paper = models.Paper(
        subject=subject,
        year=year,
        exam_session=exam_session,
        examiner=examiner,
        source_file=str(dest),
    )
    paper.questions = [models.Question(**q.model_dump()) for q in parsed]
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


@router.get("", response_model=list[schemas.PaperOut])
def list_papers(subject: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Paper).order_by(models.Paper.year.desc())
    if subject:
        query = query.filter(models.Paper.subject == subject)
    return query.all()


@router.get("/{paper_id}", response_model=schemas.PaperWithQuestions)
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.get(models.Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.delete("/{paper_id}", status_code=204)
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.get(models.Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    db.delete(paper)
    db.commit()
