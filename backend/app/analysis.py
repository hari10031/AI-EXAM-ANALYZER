"""Analysis engine: semantic deduplication, frequency/recency statistics, syllabus mapping.

All probabilities are strict math over historical data — the LLM is never involved here
(Implmentation-01.md §7, core accuracy principle).
"""

from collections import Counter, defaultdict

import numpy as np
from sqlalchemy.orm import Session

from . import models
from .config import get_settings
from .embeddings import from_json

# Topic classification: cold = never tested; hot = a mapped question group has
# recency-weighted probability at or above this; warm = anything in between.
HOT_THRESHOLD = 0.5


class AnalysisError(Exception):
    pass


def _subject_questions(db: Session, subject: str):
    return (
        db.query(models.Question, models.Paper.year)
        .join(models.Paper)
        .filter(models.Paper.subject == subject)
        .order_by(models.Paper.year, models.Question.question_number, models.Question.part, models.Question.id)
        .all()
    )


def dedup_questions(db: Session, subject: str) -> int:
    """Greedy clustering by cosine similarity: each question joins the first existing
    group whose representative (first member) is within the threshold, else starts a new
    group. Deterministic (chronological order) and O(n²), fine for hundreds of rows.
    Returns the number of groups."""
    threshold = get_settings().dedup_threshold
    rows = [(q, year) for q, year in _subject_questions(db, subject) if q.embedding]
    if not rows:
        raise AnalysisError(f"No embedded questions for subject '{subject}' — run embedding first.")

    representatives: list[np.ndarray] = []
    for question, _year in rows:
        vec = from_json(question.embedding)
        if representatives:
            sims = np.stack(representatives) @ vec
            best = int(np.argmax(sims))
            if sims[best] >= threshold:
                question.canonical_group_id = best + 1
                continue
        representatives.append(vec)
        question.canonical_group_id = len(representatives)

    db.commit()
    return len(representatives)


def frequency_table(db: Session, subject: str) -> list[dict]:
    """Per question group: P_base = years_appeared / N and recency-weighted probability
    with decay^(latest_year - year) weights (Implmentation-01.md §4 Track A)."""
    decay = get_settings().recency_decay
    rows = _subject_questions(db, subject)
    if not rows:
        raise AnalysisError(f"No papers found for subject '{subject}'.")

    all_years = sorted({year for _q, year in rows})
    latest = max(all_years)
    weights = {year: decay ** (latest - year) for year in all_years}
    total_weight = sum(weights.values())

    grouped: dict[int, list[tuple[models.Question, int]]] = defaultdict(list)
    for question, year in rows:
        if question.canonical_group_id is None:
            raise AnalysisError(f"Ungrouped questions found for '{subject}' — run analysis first.")
        grouped[question.canonical_group_id].append((question, year))

    table = []
    for group_id, members in grouped.items():
        years_appeared = sorted({year for _q, year in members})
        # representative text = most recent phrasing of the question
        representative = max(members, key=lambda m: m[1])[0]
        marks_values = [q.marks for q, _y in members if q.marks is not None]
        table.append(
            {
                "canonical_group_id": group_id,
                "question_text": representative.question_text,
                "appearances": len(members),
                "years_appeared": years_appeared,
                "p_base": round(len(years_appeared) / len(all_years), 4),
                "p_weighted": round(
                    sum(weights[y] for y in years_appeared) / total_weight, 4
                ),
                "marks": Counter(marks_values).most_common(1)[0][0] if marks_values else None,
            }
        )
    table.sort(key=lambda row: row["p_weighted"], reverse=True)
    return table


def map_topics(db: Session, subject: str) -> int:
    """Assign each embedded question to its nearest syllabus topic by cosine similarity
    (Mode 2, Track B). Replaces previous assignments. Returns questions mapped."""
    topics = (
        db.query(models.Topic)
        .filter(models.Topic.subject == subject, models.Topic.embedding.isnot(None))
        .all()
    )
    if not topics:
        raise AnalysisError(f"No embedded syllabus topics for subject '{subject}'.")

    questions = [q for q, _y in _subject_questions(db, subject) if q.embedding]
    if not questions:
        raise AnalysisError(f"No embedded questions for subject '{subject}'.")

    topic_matrix = np.stack([from_json(t.embedding) for t in topics])

    db.query(models.QuestionTopic).filter(
        models.QuestionTopic.question_id.in_([q.id for q in questions])
    ).delete(synchronize_session=False)

    for question in questions:
        sims = topic_matrix @ from_json(question.embedding)
        best = int(np.argmax(sims))
        db.add(
            models.QuestionTopic(
                question_id=question.id,
                topic_id=topics[best].id,
                similarity=round(float(sims[best]), 4),
            )
        )
    db.commit()
    return len(questions)


def topic_coverage(db: Session, subject: str) -> list[dict]:
    """Hot/cold classification per syllabus topic: which parts of the syllabus are
    frequently tested, and which have never been touched (feeds R3 'High Probability
    Surprise' in Phase 04)."""
    topics = db.query(models.Topic).filter(models.Topic.subject == subject).all()
    if not topics:
        raise AnalysisError(f"No syllabus uploaded for subject '{subject}' (Mode 2 required).")

    frequency = {row["canonical_group_id"]: row for row in frequency_table(db, subject)}

    question_rows = _subject_questions(db, subject)
    year_by_question = {q.id: year for q, year in question_rows}
    group_by_question = {q.id: q.canonical_group_id for q, _y in question_rows}

    assignments = (
        db.query(models.QuestionTopic)
        .filter(models.QuestionTopic.question_id.in_(year_by_question.keys()))
        .all()
    )
    by_topic: dict[int, list[models.QuestionTopic]] = defaultdict(list)
    for assignment in assignments:
        by_topic[assignment.topic_id].append(assignment)

    coverage = []
    for topic in topics:
        mapped = by_topic.get(topic.id, [])
        groups = {group_by_question[a.question_id] for a in mapped}
        score = max((frequency[g]["p_weighted"] for g in groups), default=0.0)
        if not mapped:
            status = "cold"
        elif score >= HOT_THRESHOLD:
            status = "hot"
        else:
            status = "warm"
        coverage.append(
            {
                "topic": topic.name,
                "chapter": topic.chapter,
                "syllabus_weight": topic.syllabus_weight,
                "status": status,
                "score": round(score, 4),
                "question_count": len(mapped),
                "years_covered": sorted({year_by_question[a.question_id] for a in mapped}),
            }
        )
    coverage.sort(key=lambda row: row["score"], reverse=True)
    return coverage
