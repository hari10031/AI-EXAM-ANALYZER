"""Generative output (Implmentation-01.md §4 Step 4): Gemini 3.1 Pro phrases the
predicted questions. Probabilities, structure, and concept selection are decided by
the pattern engine before this module runs — the LLM only words the questions."""

import json

from .config import get_settings
from .parser import ParserError, _generate_structured
from .schemas import PhrasedQuestion

PHRASE_PROMPT = """You are writing questions for a mock university exam paper.

You receive a JSON array of items. Each item has:
- slot_id: identifier to echo back
- kind: "historical" or "surprise"
- marks: marks allotted (may be null)
- source_question (historical only): a real past exam question on this concept
- topic (surprise only): a syllabus topic that has never been asked

For each item write exactly one exam-style question:
- historical: test the SAME concept at the same difficulty as source_question, freshly
  reworded as this year's version. Do not change the technical content or scope.
- surprise: a typical exam question strictly on the given topic, appropriate for the marks.
- Match the formal tone of the source questions. No preamble, no numbering, no mention
  of probabilities or predictions.

Return every slot_id from the input exactly once.

Items:
{items_json}"""


def phrase_questions(items: list[dict]) -> dict[int, str]:
    """items: [{slot_id, kind, marks, source_question|topic}]. Returns slot_id -> text.
    Raises ParserError (surfaced as 502) on any Gemini failure."""
    if not items:
        return {}
    phrased: list[PhrasedQuestion] = _generate_structured(
        PHRASE_PROMPT.format(items_json=json.dumps(items, indent=2)),
        list[PhrasedQuestion],
        model=get_settings().gemini_generate_model,
    )
    result = {p.slot_id: p.question_text for p in phrased}
    missing = {item["slot_id"] for item in items} - result.keys()
    if missing:
        raise ParserError(f"Gemini did not phrase all slots (missing {sorted(missing)}).")
    return result
