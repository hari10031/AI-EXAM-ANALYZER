from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models, schemas
from .analysis import AnalysisError
from .db import get_db
from .generator import phrase_questions
from .parser import ParserError
from .patterns import assemble_prediction

router = APIRouter(tags=["predictions"])


@router.post("/predict/{subject}", response_model=schemas.PredictionResponse, status_code=201)
def predict(subject: str, generate: bool = True, db: Session = Depends(get_db)):
    """Run the pattern engine and produce the mock paper. With generate=true (default)
    Gemini rephrases each question; with generate=false the paper uses the historical
    representative phrasings — fully offline, no API key needed."""
    try:
        assembled = assemble_prediction(db, subject)
    except AnalysisError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    all_items = assembled["items"] + assembled["surprises"]
    if generate:
        payload = []
        for slot_id, item in enumerate(all_items):
            entry: dict = {"slot_id": slot_id, "marks": item["marks"]}
            if item["basis"] == "surprise":
                entry.update(kind="surprise", topic=item["topic"])
            else:
                entry.update(kind="historical", source_question=item["question_text"])
            payload.append(entry)
        try:
            phrased = phrase_questions(payload)
        except ParserError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        for slot_id, item in enumerate(all_items):
            item["question_text"] = phrased[slot_id]

    run = models.PredictionRun(
        subject=subject,
        mode=assembled["mode"],
        generated=generate,
        items=[models.PredictionItem(**item) for item in all_items],
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return schemas.PredictionResponse(
        run=schemas.PredictionRunOut.model_validate(run),
        study_guide=assembled["study_guide"],
    )


@router.get("/predictions/{subject}", response_model=list[schemas.PredictionRunSummary])
def list_runs(subject: str, db: Session = Depends(get_db)):
    return (
        db.query(models.PredictionRun)
        .filter(models.PredictionRun.subject == subject)
        .order_by(models.PredictionRun.created_at.desc())
        .all()
    )


@router.get("/predictions/run/{run_id}", response_model=schemas.PredictionRunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(models.PredictionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Prediction run not found")
    return run
