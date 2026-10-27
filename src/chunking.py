import re
import db

# Target size of a chunk in characters (roughly 150-200 words).
MAX_CHARS = 1000

# A short field is kept whole as a single chunk (e.g. the AI-use rule), so a
# rule is never split in half. Up to this many characters.
KEEP_WHOLE_UP_TO = 1500


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _units(text: str) -> list[str]:
    """Break text into small pieces (paragraphs, then lines, then sentences)."""
    text = text.replace("\r\n", "\n").strip()
    units = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    # PDF text often has no blank lines: fall back to single line breaks.
    if len(units) == 1 and len(units[0]) > MAX_CHARS:
        units = [line.strip() for line in units[0].split("\n") if line.strip()]

    # A single huge paragraph or line: split on sentences.
    result: list[str] = []
    for u in units:
        if len(u) > MAX_CHARS:
            result.extend(_split_sentences(u))
        else:
            result.append(u)
    return result


def split_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Pack small pieces into chunks of up to max_chars, never cutting a piece in half."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= KEEP_WHOLE_UP_TO:
        return [text]

    chunks: list[str] = []
    current = ""
    for unit in _units(text):
        if current and len(current) + len(unit) + 1 > max_chars:
            chunks.append(current)
            current = unit
        else:
            current = f"{current}\n{unit}" if current else unit
    if current:
        chunks.append(current)
    return chunks


def chunk_assessment(assessment: dict) -> list[dict]:
    """Chunks for one assessment row from db.list_assessments()."""
    chunks: list[dict] = []
    for field, text in db.get_text_fields(assessment["id"]).items():
        for n, piece in enumerate(split_text(text), start=1):
            chunks.append(
                {
                    "chunk_id": f"{assessment['id']}:{field}:{n}",
                    "assessment_id": assessment["id"],
                    "module_code": assessment.get("module_code"),
                    "module_title": assessment.get("module_title"),
                    "source_file": assessment.get("source_file"),
                    "field": field,
                    "content": piece,
                }
            )
    return chunks


def build_all_chunks() -> list[dict]:
    """Chunks for every assessment in the database."""
    chunks: list[dict] = []
    for a in db.list_assessments():
        chunks.extend(chunk_assessment(a))
    return chunks


if __name__ == "__main__":
    # Quick test: python chunking.py
    all_chunks = build_all_chunks()
    print(f"{len(all_chunks)} chunks")
    for c in all_chunks[:10]:
        print(f"\n[{c['chunk_id']}] ({len(c['content'])} chars)")
        print(c["content"][:200])