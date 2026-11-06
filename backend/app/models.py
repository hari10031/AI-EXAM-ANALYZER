from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Paper(Base):
    """One uploaded past exam paper. Schema per Implmentation-01.md §5."""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(200), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    exam_session: Mapped[str | None] = mapped_column(String(50))
    examiner: Mapped[str | None] = mapped_column(String(200))
    source_file: Mapped[str] = mapped_column(String(500))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    questions: Mapped[list["Question"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan", order_by="Question.id"
    )


class Question(Base):
    """One parsed sub-question. `embedding` holds an L2-normalized JSON float array
    (portable across SQLite/Postgres; pgvector is the scale-up path).
    `canonical_group_id` links semantically identical questions across years —
    it is subject-scoped and reassigned on each dedup run."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    question_number: Mapped[int] = mapped_column(Integer)
    part: Mapped[str | None] = mapped_column(String(10))
    marks: Mapped[int | None] = mapped_column(Integer)
    question_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[str | None] = mapped_column(Text)
    canonical_group_id: Mapped[int | None] = mapped_column(Integer, index=True)

    paper: Mapped[Paper] = relationship(back_populates="questions")


class Topic(Base):
    """Syllabus topic (Mode 2). Subject column added on top of Implmentation-01.md §5
    so one database can hold multiple subjects."""

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(200), index=True)
    name: Mapped[str] = mapped_column(String(300))
    chapter: Mapped[str | None] = mapped_column(String(100))
    syllabus_weight: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[str | None] = mapped_column(Text)


class QuestionTopic(Base):
    """Nearest-topic assignment per question with its cosine similarity."""

    __tablename__ = "question_topics"

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    similarity: Mapped[float] = mapped_column(Float)


class PredictionRun(Base):
    """One prediction run for a subject. Splits Implmentation-01.md §5's `predictions`
    table into run + items for clean retrieval of past runs."""

    __tablename__ = "prediction_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(200), index=True)
    mode: Mapped[str] = mapped_column(String(30))  # "pattern-only" | "syllabus-constrained"
    generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    items: Mapped[list["PredictionItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="PredictionItem.id"
    )


class PredictionItem(Base):
    """One predicted question (or surprise candidate). probability is null for
    surprises — they have no historical recurrence to ground a number in."""

    __tablename__ = "prediction_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("prediction_runs.id", ondelete="CASCADE"), index=True
    )
    question_number: Mapped[int | None] = mapped_column(Integer)
    part: Mapped[str | None] = mapped_column(String(10))
    marks: Mapped[int | None] = mapped_column(Integer)
    question_text: Mapped[str] = mapped_column(Text)
    probability: Mapped[float | None] = mapped_column(Float)
    basis: Mapped[str] = mapped_column(String(30))  # "rotation" | "frequency" | "frequency-global" | "surprise"
    rationale: Mapped[str | None] = mapped_column(Text)
    canonical_group_id: Mapped[int | None] = mapped_column(Integer)
    topic: Mapped[str | None] = mapped_column(String(300))

    run: Mapped[PredictionRun] = relationship(back_populates="items")
