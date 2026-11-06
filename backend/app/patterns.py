"""Pattern logic engine (Implmentation-01.md §4 Step 3): turns analysis output into a
predicted paper. Pure math and rules — the LLM is only used afterwards to phrase.

Rules implemented:
- R1 (frequency): every predicted question carries its group's recency-weighted
  probability from the frequency table; nothing is invented.
- R2 (structure enforcement): the paper blueprint is the set of question slots
  (number, part) that appear in >= slot_min_share of historical years, with each
  slot's typical marks.
- R3 (surprise): syllabus topics never asked but carrying syllabus weight are
  flagged as surprise candidates with probability = null (no history to ground one).
"""

from collections import Counter, defaultdict
from statistics import median

from sqlalchemy.orm import Session

from .analysis import AnalysisError, _subject_questions, frequency_table, topic_coverage
from .config import get_settings


def detect_rotation(sequence: list[int]) -> tuple[int, int] | None:
    """If a cycle of length 2 or 3 with at least 2 distinct concepts explains the whole
    slot history (and at least one full repeat was observed), return
    (predicted_next_group, cycle_length). A constant sequence is not a rotation."""
    for k in (2, 3):
        if (
            len(sequence) >= k + 1
            and len(set(sequence)) >= 2
            and all(sequence[i] == sequence[i - k] for i in range(k, len(sequence)))
        ):
            return sequence[len(sequence) - k], k
    return None


def assemble_prediction(db: Session, subject: str) -> dict:
    """Build the predicted paper: blueprint slots filled by rotation or frequency,
    plus surprise candidates (Mode 2) and the study guide."""
    settings = get_settings()
    frequency = frequency_table(db, subject)  # raises AnalysisError if not analyzed
    freq_by_group = {row["canonical_group_id"]: row for row in frequency}

    rows = _subject_questions(db, subject)
    if any(q.canonical_group_id is None for q, _y in rows):
        raise AnalysisError(f"Ungrouped questions found for '{subject}' — run analysis first.")

    all_years = sorted({year for _q, year in rows})
    n_years = len(all_years)

    # slot -> {year -> (question, group)}; first occurrence per year wins (choice papers)
    slots: dict[tuple[int, str | None], dict[int, object]] = defaultdict(dict)
    per_year_counts: Counter = Counter()
    for question, year in rows:
        per_year_counts[year] += 1
        slots[(question.question_number, question.part)].setdefault(year, question)

    blueprint = sorted(
        (slot for slot, by_year in slots.items() if len(by_year) / n_years >= settings.slot_min_share),
        key=lambda slot: (slot[0], slot[1] or ""),
    )

    used_groups: set[int] = set()
    items: list[dict] = []

    def frequency_pick(candidate_groups: list[int], basis: str) -> tuple[int, str] | None:
        ranked = sorted(
            (g for g in candidate_groups if g not in used_groups),
            key=lambda g: freq_by_group[g]["p_weighted"],
            reverse=True,
        )
        return (ranked[0], basis) if ranked else None

    for slot in blueprint:
        by_year = slots[slot]
        sequence = [by_year[year].canonical_group_id for year in sorted(by_year)]
        rotation = detect_rotation(sequence)

        pick = None
        if rotation and rotation[0] not in used_groups:
            group, cycle = rotation
            pick = (group, "rotation")
            rationale_extra = f"; slot cycles through {len(set(sequence))} concepts (period {cycle}), this is next in rotation"
        else:
            pick = frequency_pick(sequence, "frequency")
            rationale_extra = ""
        if pick is None:
            pick = frequency_pick(list(freq_by_group), "frequency-global")
        if pick is None:
            continue  # more slots than distinct question groups

        group, basis = pick
        used_groups.add(group)
        row = freq_by_group[group]
        marks_values = [q.marks for q in by_year.values() if q.marks is not None]
        years_str = ", ".join(map(str, row["years_appeared"]))
        items.append(
            {
                "question_number": slot[0],
                "part": slot[1],
                "marks": Counter(marks_values).most_common(1)[0][0] if marks_values else row["marks"],
                "question_text": row["question_text"],
                "probability": row["p_weighted"],
                "basis": basis,
                "rationale": f"Asked in {years_str} — {row['appearances']}x in {n_years} years"
                f" (p_base {row['p_base']}){rationale_extra}",
                "canonical_group_id": group,
                "topic": None,
            }
        )

    if not items:
        # Irregular papers with no stable slots: flat paper of the top groups,
        # sized to the median question count per year.
        size = max(1, round(median(per_year_counts.values())))
        for index, row in enumerate(frequency[:size], start=1):
            items.append(
                {
                    "question_number": index,
                    "part": None,
                    "marks": row["marks"],
                    "question_text": row["question_text"],
                    "probability": row["p_weighted"],
                    "basis": "frequency",
                    "rationale": f"Asked {row['appearances']}x in {n_years} years (p_base {row['p_base']})",
                    "canonical_group_id": row["canonical_group_id"],
                    "topic": None,
                }
            )

    # R3 — surprise candidates (Mode 2 only)
    surprises: list[dict] = []
    try:
        coverage = topic_coverage(db, subject)
    except AnalysisError:
        coverage = None  # no syllabus -> Mode 1

    if coverage is not None:
        cold = [row for row in coverage if row["status"] == "cold"]
        cold.sort(key=lambda row: row["syllabus_weight"] or 0, reverse=True)
        for row in cold[: settings.surprise_count]:
            weight_str = f" (syllabus weight {row['syllabus_weight']})" if row["syllabus_weight"] else ""
            surprises.append(
                {
                    "question_number": None,
                    "part": None,
                    "marks": None,
                    "question_text": f"[Surprise candidate] {row['topic']}"
                    + (f" — {row['chapter']}" if row["chapter"] else ""),
                    "probability": None,
                    "basis": "surprise",
                    "rationale": f"In syllabus{weight_str} but never asked in {n_years} years",
                    "canonical_group_id": None,
                    "topic": row["topic"],
                }
            )

    return {
        "mode": "syllabus-constrained" if coverage is not None else "pattern-only",
        "items": items,
        "surprises": surprises,
        "study_guide": frequency[: settings.study_guide_size],
    }
