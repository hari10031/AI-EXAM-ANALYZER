"""Gemini-powered parsing: raw extracted text -> structured records.

Uses Gemini structured output (response_schema) so the model must return valid JSON —
per the core design principle, the LLM only structures text; all metadata
(subject/year/session) comes from the upload form.
"""

from google import genai

from .config import get_settings
from .schemas import ParsedQuestion, ParsedTopic


class ParserError(Exception):
    pass


PARSE_PROMPT = """You are parsing the raw extracted text of a university exam question paper.

Extract EVERY question and sub-question as a separate record:
- question_number: the main question number (integer). "Q2(a)" -> 2.
- part: the sub-part letter in lowercase ("a", "b", ...) or null if the question has no parts.
- marks: the marks for that question/part if printed (e.g. "[5M]", "(10 marks)"), else null.
- question_text: the complete question text, cleaned of numbering, marks annotations, and OCR artifacts. Keep formulas/code as written.

Rules:
- Do NOT invent, merge, summarize, or reword questions.
- If the paper offers a choice (e.g. "Q2 OR Q3"), extract both as separate records.
- Ignore headers, footers, instructions to candidates, and page numbers.

Paper text:
---
{text}
---"""

TOPIC_PROMPT = """You are parsing the raw extracted text of a university course syllabus.

Extract every distinct topic as a separate record:
- name: concise topic name at concept level (e.g. "Binary Search Trees", not a whole unit title when sub-topics are listed).
- chapter: the unit/chapter identifier it belongs to (e.g. "Unit III", "Chapter 2"), else null.
- syllabus_weight: allotted hours or marks weight if stated, else null.

Rules:
- Do NOT invent topics that are not in the text.
- Ignore course objectives, outcomes, textbook lists, and administrative text.

Syllabus text:
---
{text}
---"""


def _generate_structured(prompt: str, schema, model: str | None = None):
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ParserError(
            "GEMINI_API_KEY is not set. Copy backend/.env.example to backend/.env and add "
            "your key (free at https://aistudio.google.com/apikey)."
        )

    client = genai.Client(api_key=settings.gemini_api_key)
    try:
        response = client.models.generate_content(
            model=model or settings.gemini_parse_model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": schema,
                "temperature": 0,
            },
        )
    except Exception as exc:
        raise ParserError(f"Gemini parsing call failed: {exc}") from exc

    if not response.parsed:
        raise ParserError("Gemini returned no records — check the extracted text quality.")
    return response.parsed


def parse_questions(paper_text: str) -> list[ParsedQuestion]:
    return _generate_structured(PARSE_PROMPT.format(text=paper_text), list[ParsedQuestion])


def parse_topics(syllabus_text: str) -> list[ParsedTopic]:
    return _generate_structured(TOPIC_PROMPT.format(text=syllabus_text), list[ParsedTopic])
