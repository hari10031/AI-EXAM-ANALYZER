from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pathlib import Path

from sqlalchemy.orm import Session

from . import models, schemas
from .analysis import AnalysisError, dedup_questions, frequency_table, map_topics, topic_coverage
from .config import get_settings
from .db import get_db
from .embeddings import EmbeddingError, embed_texts, to_json
from .ocr import ExtractionError, extract_text
from .parser import ParserError, parse_topics

router = APIRouter(tags=["analysis"])


@router.post("/syllabus", response_model=list[schemas.TopicOut], status_code=201)
async def upload_syllabus(
    file: UploadFile,
    subject: str = Form(...),
    db: Session = Depends(get_db),
):
    """Upload the official syllabus (Mode 2): extract text, parse topics via Gemini,
    replace any previously stored topics for the subject."""
    settings = get_settings()
    storage = Path(settings.storage_dir).parent / "syllabus"
    storage.mkdir(parents=True, exist_ok=True)
    dest = storage / f"{subject}_{file.filename or 'syllabus.pdf'}".replace(" ", "_")
    dest.write_bytes(await file.read())

    try:
        raw_text = extract_text(dest)
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        parsed = parse_topics(raw_text)
    except ParserError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    old_topics = db.query(models.Topic).filter(models.Topic.subject == subject).all()
    if old_topics:
        db.query(models.QuestionTopic).filter(
            models.QuestionTopic.topic_id.in_([t.id for t in old_topics])
        ).delete(synchronize_session=False)
        for topic in old_topics:
            db.delete(topic)

    topics = [models.Topic(subject=subject, **t.model_dump()) for t in parsed]
    db.add_all(topics)
    db.commit()
    for topic in topics:
        db.refresh(topic)
    return topics


@router.get("/syllabus/{subject}", response_model=list[schemas.TopicOut])
def get_syllabus(subject: str, db: Session = Depends(get_db)):
    topics = db.query(models.Topic).filter(models.Topic.subject == subject).all()
    if not topics:
        raise HTTPException(status_code=404, detail=f"No syllabus uploaded for '{subject}'.")
    return topics


@router.post("/analysis/{subject}/run", response_model=schemas.AnalysisSummary)
def run_analysis(subject: str, db: Session = Depends(get_db)):
    """Full analysis pass: embed anything missing embeddings, dedup questions into
    canonical groups, and (if a syllabus exists) map questions to topics."""
    questions = (
        db.query(models.Question)
        .join(models.Paper)
        .filter(models.Paper.subject == subject)
        .all()
    )
    if not questions:
        raise HTTPException(status_code=404, detail=f"No papers found for subject '{subject}'.")

    topics = db.query(models.Topic).filter(models.Topic.subject == subject).all()

    try:
        pending_questions = [q for q in questions if q.embedding is None]
        question_vectors = (
            embed_texts([q.question_text for q in pending_questions]) if pending_questions else []
        )
        for question, vector in zip(pending_questions, question_vectors, strict=True):
            question.embedding = to_json(vector)

        pending_topics = [t for t in topics if t.embedding is None]
        topic_texts = [f"{t.name} — {t.chapter}" if t.chapter else t.name for t in pending_topics]
        topic_vectors = embed_texts(topic_texts) if pending_topics else []
        for topic, vector in zip(pending_topics, topic_vectors, strict=True):
            topic.embedding = to_json(vector)
        db.commit()

        groups = dedup_questions(db, subject)
        questions_mapped = map_topics(db, subject) if topics else 0
    except EmbeddingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AnalysisError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return schemas.AnalysisSummary(
        subject=subject,
        mode="syllabus-constrained" if topics else "pattern-only",
        questions_embedded=len(pending_questions),
        topics_embedded=len(pending_topics),
        groups=groups,
        questions_mapped=questions_mapped,
    )


@router.get("/analysis/{subject}/frequency", response_model=list[schemas.FrequencyRow])
def get_frequency(subject: str, db: Session = Depends(get_db)):
    """Ranked question groups with base and recency-weighted probabilities —
    the Phase 03 deliverable table."""
    try:
        return frequency_table(db, subject)
    except AnalysisError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/analysis/{subject}/coverage", response_model=list[schemas.CoverageRow])
def get_coverage(subject: str, db: Session = Depends(get_db)):
    """Hot/warm/cold syllabus coverage (Mode 2). Cold + high syllabus_weight topics
    are Phase 04's 'High Probability Surprise' candidates."""
    try:
        return topic_coverage(db, subject)
    except AnalysisError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
