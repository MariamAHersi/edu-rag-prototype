import sys
from datetime import date
from pathlib import Path
from typing import Any, cast, get_args, get_origin

from dotenv import load_dotenv

load_dotenv()  

import pymupdf  
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pydantic import ValidationError

import db
import llm
from schema import AssessmentBrief

SUPPORTED = {".pdf", ".docx"}


LIST_TABLES = {"learning_outcomes", "submission_checklist"}


# ---------- 1. text extraction ----------

def extract_text_pdf(path: Path) -> str:
    doc = pymupdf.open(path)
    pages = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        pages.append(f"[PAGE {i + 1}]\n{page.get_text()}")
    doc.close()
    return "\n\n".join(pages)


def extract_text_docx(path: Path) -> str:
    """Paragraphs and tables in document order; table rows come out as 'cell | cell | cell'."""
    doc = Document(str(path))
    lines: list[str] = []
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = Paragraph(child, doc).text.strip() 
            if text:
                lines.append(text)
        elif tag == "tbl":
            table = Table(child, doc) 
            for row in table.rows:
                seen = set()
                cells = []
                for cell in row.cells:
                    if cell._tc in seen:  
                        continue
                    seen.add(cell._tc)
                    cells.append(cell.text.strip().replace("\n", " "))
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_pdf(path)
    elif suffix == ".docx":
        return extract_text_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {path.name} (use .pdf or .docx)")


# ---------- 2. Gemini extraction ----------

def extract_brief(text: str) -> AssessmentBrief:
    prompt = (
        "Extract the assessment brief details from the document below. "
        "Only use information stated in the document. "
        "Use null for anything not stated. Do not guess.\n\n"
        f"DOCUMENT:\n{text}"
    )
    raw = llm.ask(prompt, response_schema=AssessmentBrief)
    return AssessmentBrief.model_validate_json(raw)


# ---------- 3. saving to MySQL ----------

def _flatten(annotation):
    """The annotation and every type nested inside it (list[str] | None -> list[str], str, NoneType...)."""
    yield annotation
    for inner in get_args(annotation):
        yield from _flatten(inner)


def _is_list_field(annotation) -> bool:
    """True for list[...] and Optional list[...] fields; these are saved in their own tables."""
    return any(get_origin(a) is list for a in _flatten(annotation))


def list_fields() -> set[str]:
    return {n for n, f in AssessmentBrief.model_fields.items() if _is_list_field(f.annotation)}


def _sql_type(annotation) -> str:
    kinds = set(_flatten(annotation))
    if date in kinds:
        return "DATE"
    if int in kinds:
        return "INT"
    if float in kinds:
        return "FLOAT"
    return "LONGTEXT"


def schema_problems() -> list[str]:
    """Things in schema.py that the database doesn't have yet, each with the SQL to fix it."""
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SHOW COLUMNS FROM assessments")
        columns = {str(r[0]) for r in cast(list[tuple[Any, ...]], cur.fetchall())}
        cur.execute("SHOW TABLES")
        tables = {str(r[0]) for r in cast(list[tuple[Any, ...]], cur.fetchall())}
    finally:
        conn.close()

    problems: list[str] = []
    lists = list_fields()
    for name, field in AssessmentBrief.model_fields.items():
        if name in lists:
            continue
        if name not in columns:
            problems.append(
                f"No column '{name}' in the assessments table. Add it with:\n"
                f"      ALTER TABLE assessments ADD COLUMN {name} {_sql_type(field.annotation)};"
            )

    needed = {t for t in LIST_TABLES if t in lists}
    if "marking_criteria" in lists:
        needed |= {"criteria", "grade_bands"}
    for t in sorted(needed - tables):
        if t in LIST_TABLES:
            problems.append(
                f"No table '{t}'. Create it with:\n"
                f"      CREATE TABLE {t} (id INT AUTO_INCREMENT PRIMARY KEY, assessment_id INT NOT NULL, "
                f"text TEXT, FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE);"
            )
        else:
            problems.append(f"No table '{t}'. Create it using the CREATE TABLE statement from earlier.")
    return problems


def save_brief(brief: AssessmentBrief, source_file: str) -> int:
    """Insert or update the main row and return its id.

    Any list field in schema.py (outcomes, rubric, checklist...) goes in its own
    table, so it is left out of this insert automatically.
    """
    lists = list_fields()
    data: dict[str, Any] = {"source_file": source_file}
    data.update({k: v for k, v in brief.model_dump().items() if k not in lists})

    columns = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    updates = ", ".join(f"{col}=VALUES({col})" for col in data if col != "source_file")

    sql = f"""
        INSERT INTO assessments ({columns})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE {updates}
    """

    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, list(data.values()))
        conn.commit()
    finally:
        conn.close()

    assessment_id = db.find_assessment_id_by_file(source_file)
    if assessment_id is None:
        raise RuntimeError(f"Saved {source_file} but could not find it again")
    return assessment_id


def save_list_items(table: str, assessment_id: int, items: list[str]) -> None:
    if table not in LIST_TABLES:
        raise ValueError(f"Unknown list table: {table}")
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {table} WHERE assessment_id = %s", (assessment_id,))
        for item in items:
            cur.execute(
                f"INSERT INTO {table} (assessment_id, text) VALUES (%s, %s)",
                (assessment_id, item),
            )
        conn.commit()
    finally:
        conn.close()


def save_rubric(brief: AssessmentBrief, assessment_id: int) -> None:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        # clear the old rubric so re-running doesn't duplicate rows
        cur.execute("DELETE FROM criteria WHERE assessment_id = %s", (assessment_id,))

        for c in brief.marking_criteria:
            cur.execute(
                "INSERT INTO criteria (assessment_id, name, description, weighting_percent) "
                "VALUES (%s, %s, %s, %s)",
                (assessment_id, c.name, c.description, c.weighting_percent),
            )
            criterion_id = cur.lastrowid
            for b in c.grade_bands:
                cur.execute(
                    "INSERT INTO grade_bands (criterion_id, band_name, descriptor) "
                    "VALUES (%s, %s, %s)",
                    (criterion_id, b.band_name, b.descriptor),
                )
        conn.commit()
    finally:
        conn.close()


# ---------- 4. putting it together ----------

def ingest_file(path: Path) -> int:
    """Run the whole pipeline for one file and return the assessment id."""
    source_file = path.name  # the label stored in MySQL; always the real file name

    text = extract_text(path)
    print(f"  extracted {len(text):,} characters of text")

    brief = extract_brief(text)

    assessment_id = save_brief(brief, source_file)
    lists = list_fields()
    for table in sorted(LIST_TABLES & lists):
        save_list_items(table, assessment_id, getattr(brief, table) or [])
    if "marking_criteria" in lists:
        save_rubric(brief, assessment_id)

    def count(name: str) -> int:
        value = getattr(brief, name, None)
        return len(value) if isinstance(value, list) else 0

    print(
        f"  saved assessment {assessment_id}: "
        f"{count('learning_outcomes')} learning outcomes, "
        f"{count('marking_criteria')} criteria, "
        f"{count('submission_checklist')} checklist items"
    )
    return assessment_id


def find_files(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(p for p in target.iterdir() if p.suffix.lower() in SUPPORTED)
    return [target]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1

    target = Path(argv[1])
    if not target.exists():
        print(f"Not found: {target}")
        return 1

    files = find_files(target)
    if not files:
        print(f"No .pdf or .docx files in {target}")
        return 1

    problems = schema_problems()
    if problems:
        print("The database doesn't match schema.py yet. Fix these in MySQL Workbench, then run this again:\n")
        for p in problems:
            print(f"  - {p}")
        return 1

    failed: list[str] = []
    for path in files:
        print(f"\n{path.name}")
        try:
            ingest_file(path)
        except ValidationError as e:
            print(f"  FAILED validation:\n{e}")
            failed.append(path.name)
        except llm.LLMUnavailable as e:
            print(f"  FAILED, Gemini unavailable: {e}")
            failed.append(path.name)
        except ValueError as e:
            print(f"  FAILED: {e}")
            failed.append(path.name)

    print(f"\nDone: {len(files) - len(failed)} of {len(files)} file(s) ingested.")
    if failed:
        print("Failed: " + ", ".join(failed) + "  (re-run to retry; finished files are cached)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))