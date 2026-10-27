import db
import llm

SYSTEM_INSTRUCTION = """You are an assistant that helps university students understand their assessment brief.

Rules:
- Answer using ONLY the assessment brief data provided. If the answer is not in the data, say it is not stated in the brief and suggest checking with the module leader or the module page.
- Never invent deadlines, word counts, marks, grade boundaries or rules.
- For rules and requirements (especially referencing and the use of AI), stay close to the brief's own wording.
- The original brief may contain images, figures or examples that are not included in the data. If a question seems to depend on one, say so instead of guessing.
- Do not write the student's assignment for them. You can explain what the task asks, what the marking criteria mean and what the rules are.
- Keep answers short, clear and in plain English, using UK spelling."""


def _title(key: str) -> str:
    return key.replace("_", " ").capitalize()


def format_context(data: dict, include_text: bool = True) -> str:
    """Turn the stored record into labelled plain text for the prompt.

    include_text=False leaves out the long text sections (retrieval mode adds
    the relevant chunks separately).
    """
    parts: list[str] = []

    facts = data.get("facts")
    if facts:
        lines = [f"- {_title(k)}: {v}" for k, v in facts.items() if k != "id" and v not in (None, "")]
        parts.append("KEY FACTS\n" + "\n".join(lines))

    outcomes = data.get("learning_outcomes") or []
    if outcomes:
        parts.append("LEARNING OUTCOMES\n" + "\n".join(f"- {o}" for o in outcomes))

    criteria = data.get("criteria") or []
    if criteria:
        blocks = []
        for c in criteria:
            head = c.get("name") or "Unnamed criterion"
            if c.get("weighting_percent") is not None:
                head += f" ({c['weighting_percent']}%)"
            lines = [head]
            if c.get("description"):
                lines.append(c["description"])
            for b in c.get("grade_bands") or []:
                lines.append(f"  - {b.get('band_name') or 'Band'}: {b.get('descriptor') or 'not stated'}")
            blocks.append("\n".join(lines))
        parts.append("MARKING CRITERIA AND GRADE BANDS\n" + "\n\n".join(blocks))

    checklist = data.get("submission_checklist") or []
    if checklist:
        parts.append("SUBMISSION CHECKLIST\n" + "\n".join(f"- {i}" for i in checklist))

    if include_text:
        for field, text in (data.get("text") or {}).items():
            parts.append(f"{_title(field).upper()}\n{text}")

    return "\n\n".join(parts) if parts else "No data stored for this assessment."


def format_chunks(chunks: list[dict]) -> str:
    if not chunks:
        return "(no relevant sections found)"
    return "\n\n".join(f"[{i}] {_title(c['field'])}:\n{c['content']}" for i, c in enumerate(chunks, 1))


def _search_query(question: str, history: list[dict] | None) -> str:
    """Short follow-ups ('what about the second one?') borrow the previous question for context."""
    if history and len(question.split()) < 8:
        previous = [m["content"] for m in history if m["role"] == "user"]
        if previous:
            return f"{previous[-1]} {question}"
    return question


def answer_question(
    question: str,
    assessment_id: int,
    history: list[dict] | None = None,
    store=None,
    top_k: int = 4,
) -> tuple[str, list[dict]]:
    """Answer one question about one assessment.

    history: earlier messages as [{"role": "user"|"assistant", "content": "..."}].
    store:   an embedding.SimpleVectorStore to use retrieval, or None for the baseline.
    Returns (answer, retrieved_chunks).
    """
    data = db.get_full_assessment(assessment_id)

    chunks: list[dict] = []
    if store is not None:
        chunks = store.retrieve(_search_query(question, history), assessment_id, top_k=top_k)
        context = (
            f"{format_context(data, include_text=False)}\n\n"
            f"RELEVANT SECTIONS OF THE BRIEF\n{format_chunks(chunks)}"
        )
    else:
        context = format_context(data)

    convo = ""
    if history:
        convo = "\n".join(
            f"{'Student' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in history[-6:]
        )

    prompt = (
        f"ASSESSMENT BRIEF DATA\n{context}\n\n"
        f"CONVERSATION SO FAR\n{convo or '(none)'}\n\n"
        f"STUDENT QUESTION\n{question}"
    )
    return llm.ask(prompt, system_instruction=SYSTEM_INSTRUCTION), chunks


if __name__ == "__main__":
    # Quick test without Streamlit:  python qa.py
    import embedding

    store = embedding.SimpleVectorStore()
    store.ensure_index()
    first = db.list_assessments()[0]["id"]
    answer, found = answer_question("Am I allowed to use AI?", first, store=store)
    print(answer)
    print("\nRetrieved:", [c["chunk_id"] for c in found])