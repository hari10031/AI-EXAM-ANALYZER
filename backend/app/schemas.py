from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ParsedQuestion(BaseModel):
    """What Gemini extracts from raw paper text. Year/session/subject come from the
    upload form (authoritative), not from the LLM — smaller hallucination surface."""

    question_number: int = Field(description="Main question number, e.g. 2 for question 2a")
    part: str | None = Field(default=None, description="Sub-part letter like 'a', 'b'; null if the question has no parts")
    marks: int | None = Field(default=None, description="Marks allotted, if printed on the paper")
    question_text: str = Field(description="Full question text, cleaned of numbering artifacts")


class ParsedTopic(BaseModel):
    """What Gemini extracts from raw syllabus text (Mode 2)."""

    name: str = Field(description="Concise concept-level topic name")
    chapter: str | None = Field(default=None, description="Unit/chapter identifier like 'Unit III'; null if not stated")
    syllabus_weight: int | None = Field(default=None, description="Allotted hours or marks weight if stated, else null")


class QuestionOut(ParsedQuestion):
    model_config = ConfigDict(from_attributes=True)

    id: int


class PaperOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    year: int
    exam_session: str | None
    examiner: str | None
    source_file: str
    uploaded_at: datetime


class PaperWithQuestions(PaperOut):
    questions: list[QuestionOut]


class TopicOut(ParsedTopic):
    model_config = ConfigDict(from_attributes=True)

    id: int


class AnalysisSummary(BaseModel):
    subject: str
    mode: str  # "pattern-only" | "syllabus-constrained"
    questions_embedded: int
    topics_embedded: int
    groups: int
    questions_mapped: int


class FrequencyRow(BaseModel):
    canonical_group_id: int
    question_text: str
    appearances: int
    years_appeared: list[int]
    p_base: float
    p_weighted: float
    marks: int | None


class CoverageRow(BaseModel):
    topic: str
    chapter: str | None
    syllabus_weight: int | None
    status: str  # "hot" | "warm" | "cold"
    score: float
    question_count: int
    years_covered: list[int]


class PhrasedQuestion(BaseModel):
    """Gemini generation response schema: one freshly phrased question per slot."""

    slot_id: int = Field(description="The slot_id from the input item, echoed back unchanged")
    question_text: str = Field(description="The freshly phrased exam question for this slot")


class PredictionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_number: int | None
    part: str | None
    marks: int | None
    question_text: str
    probability: float | None
    basis: str
    rationale: str | None
    canonical_group_id: int | None
    topic: str | None


class PredictionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    mode: str
    generated: bool
    created_at: datetime
    items: list[PredictionItemOut]


class PredictionRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    mode: str
    generated: bool
    created_at: datetime


class PredictionResponse(BaseModel):
    run: PredictionRunOut
    study_guide: list[FrequencyRow]
