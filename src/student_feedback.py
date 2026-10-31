import re
import tempfile
from pathlib import Path

import db
import llm
import qa
from ingest import extract_text

MIN_WORDS = 30  # below this there is nothing meaningful to give feedback on

SYSTEM_INSTRUCTION = """You are an academic tutor giving formative feedback on a student's draft, so that they can improve it before they submit.

Rules:
- Judge the draft ONLY against the assessment brief and marking criteria provided. Do not invent criteria, requirements or rules.
- Give feedback, not a mark. Do not state or predict a grade, mark or percentage. Naming the grade band whose descriptor the draft currently matches is fine.
- Do not rewrite the student's work or write new content for them. Point to where something is missing or weak and say what to do about it.
- Support each point with evidence from the draft: refer to a specific section or use a very short quote (under 15 words). Never praise or criticise something without pointing to where it appears.
- Use the word count given in the automatic checks. Do not count words yourself.
- If the draft does not yet contain enough to judge a criterion, say so instead of guessing.
- If the brief restricts the use of AI, remind the student politely to follow that rule. Never accuse them of using AI.
- Be constructive and supportive, in plain English with UK spelling.
- Finish by noting that this is automated feedback to help them improve, and that their lecturer's marking may differ.
- The original brief may contain images or examples that are not included in the data."""


def count_words(text: str) -> int:
    return len(text.split())


def word_count_check(n_words: int, limit: int | None) -> str:
    """A factual one-line check of the draft length against the brief's word limit."""
    if not limit:
        return f"{n_words:,} words (the brief states no word limit)."
    if n_words > limit:
        return f"{n_words:,} words: {n_words - limit:,} over the {limit:,}-word limit."
    return f"{n_words:,} words: {round(100 * n_words / limit)}% of the {limit:,}-word limit."


def read_draft_file(filename: str, data: bytes) -> str:
    """Text of an uploaded draft (.txt, .pdf or .docx)."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return data.decode("utf-8", errors="replace").strip()
    if suffix not in {".pdf", ".docx"}:
        raise ValueError(f"Unsupported file type: {filename} (use .pdf, .docx or .txt)")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"draft{suffix}"
        path.write_bytes(data)
        text = extract_text(path)
    return re.sub(r"\[PAGE \d+\]\n?", "", text).strip()  # drop the page markers used for briefs


def build_feedback_prompt(draft_text: str, assessment_id: int) -> str:
    data = db.get_full_assessment(assessment_id)
    if not data.get("facts"):
        raise ValueError(f"No assessment found with id {assessment_id}")

    limit = data["facts"].get("word_count")
    checks = word_count_check(count_words(draft_text), limit)

    return f"""OFFICIAL ASSESSMENT BRIEF AND MARKING CRITERIA
{qa.format_context(data)}

AUTOMATIC CHECKS (calculated by the system; use these figures)
- Draft length: {checks}

STUDENT DRAFT
\"\"\"
{draft_text}
\"\"\"

INSTRUCTIONS
Write the feedback using exactly these headings:

## 1. Alignment with the brief
Does the draft address the task, the scope and the required deliverables? Mention the word count using the automatic check above.

## 2. Marking criteria
For EACH marking criterion in the brief (use its name exactly as given):
- Which grade band the draft currently matches best (by band name only), with a one-sentence reason that points to evidence in the draft.
- What would move it into the next band up, based on that band's descriptor.
If a criterion has no band descriptors, comment on it qualitatively. If the draft does not yet contain enough to judge it, say so.

## 3. Strengths
2 to 3 things done well, each with evidence from the draft.

## 4. Priority improvements
The 3 changes that would make the biggest difference, most important first.

## 5. Before you submit
Check the draft against the submission checklist and the brief's rules (referencing, layout, use of AI). Say which items the text shows are met or missing. List separately the items that cannot be judged from the text, such as a cover sheet or file format, so the student can check them themselves.
"""


def give_feedback(draft_text: str, assessment_id: int) -> dict:
    """Feedback for one draft.

    Returns {"feedback": str, "word_count": int, "word_limit": int | None, "word_check": str}.
    Raises ValueError if the draft is too short to assess.
    """
    draft_text = draft_text.strip()
    n_words = count_words(draft_text)
    if n_words < MIN_WORDS:
        raise ValueError(
            f"The draft is only {n_words} words. Paste or upload a longer section "
            f"(at least {MIN_WORDS} words) to get useful feedback."
        )

    prompt = build_feedback_prompt(draft_text, assessment_id)
    feedback = llm.ask(prompt, system_instruction=SYSTEM_INSTRUCTION, use_cache=False)

    facts = db.get_assessment(assessment_id) or {}
    limit = facts.get("word_count")
    return {
        "feedback": feedback,
        "word_count": n_words,
        "word_limit": limit,
        "word_check": word_count_check(n_words, limit),
    }