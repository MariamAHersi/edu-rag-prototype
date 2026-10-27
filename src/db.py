import os
from typing import Any, cast

import mysql.connector

# A row from a dictionary cursor: column name -> value.
Row = dict[str, Any]

# Long free-text columns on the assessments table (these get chunked/embedded).
TEXT_FIELDS = [
    "task_description",
    "success_guidance",
    "layout_style_guidance",
    "referencing",
    "employability_professional_skills",
    "ai_use",
    "ethical_requirements",
]

# Short factual columns on the assessments table (answered straight from SQL).
FACT_FIELDS = [
    "source_file",
    "programme",
    "module_code",
    "module_title",
    "module_level",
    "assessment_type",
    "weighting_percent",
    "word_count",
    "duration_minutes",
    "deadline",
    "deadline_raw",
    "feedback_date",
    "feedback_date_raw",
    "submission_format",
]


def get_connection():
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ.get("MYSQL_DATABASE", "rag_system"),
    )


def _fetch_all(sql: str, params: tuple = ()) -> list[Row]:
    """Run a SELECT and return every row as a dict."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cast(list[Row], cur.fetchall())
    finally:
        conn.close()


def _fetch_one(sql: str, params: tuple = ()) -> Row | None:
    """Run a SELECT and return the first row as a dict, or None if there isn't one."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cast(Row | None, cur.fetchone())
    finally:
        conn.close()


# ---------- finding assessments ----------

def list_assessments() -> list[Row]:
    """For the Streamlit selector: id, module code, title, source file."""
    return _fetch_all(
        "SELECT id, module_code, module_title, assessment_type, source_file "
        "FROM assessments ORDER BY module_code, id"
    )


def find_assessment_id(module_code: str) -> int | None:
    """Look up an assessment id by module code (returns None if not found)."""
    row = _fetch_one(
        "SELECT id FROM assessments WHERE module_code = %s ORDER BY id LIMIT 1",
        (module_code,),
    )
    return row["id"] if row else None


def find_assessment_id_by_file(source_file: str) -> int | None:
    """Look up an assessment id by the file name it was ingested from (None if not found)."""
    row = _fetch_one(
        "SELECT id FROM assessments WHERE source_file = %s",
        (source_file,),
    )
    return int(row["id"]) if row else None


# ---------- facts ----------

def get_assessment(assessment_id: int) -> Row | None:
    """Short factual fields (deadline, word count, weighting, ...)."""
    cols = ", ".join(FACT_FIELDS)
    return _fetch_one(
        f"SELECT id, {cols} FROM assessments WHERE id = %s",
        (assessment_id,),
    )


# ---------- long text ----------

def get_text_fields(assessment_id: int) -> dict[str, str]:
    """Long text sections as {field_name: text}; empty sections are left out."""
    cols = ", ".join(TEXT_FIELDS)
    row = _fetch_one(
        f"SELECT {cols} FROM assessments WHERE id = %s",
        (assessment_id,),
    )
    if not row:
        return {}
    return {k: v for k, v in row.items() if v and str(v).strip()}


# ---------- lists ----------

def get_learning_outcomes(assessment_id: int) -> list[str]:
    rows = _fetch_all(
        "SELECT text FROM learning_outcomes WHERE assessment_id = %s ORDER BY id",
        (assessment_id,),
    )
    return [r["text"] for r in rows]


def get_submission_checklist(assessment_id: int) -> list[str]:
    rows = _fetch_all(
        "SELECT text FROM submission_checklist WHERE assessment_id = %s ORDER BY id",
        (assessment_id,),
    )
    return [r["text"] for r in rows]


def get_criteria(assessment_id: int) -> list[Row]:
    """Marking criteria, each with its grade bands nested inside:
    [{"name":..., "description":..., "weighting_percent":..., "grade_bands":[{"band_name":..., "descriptor":...}]}]
    """
    rows = _fetch_all(
        """
        SELECT c.id AS criterion_id, c.name, c.description, c.weighting_percent,
               b.band_name, b.descriptor
        FROM criteria c
        LEFT JOIN grade_bands b ON b.criterion_id = c.id
        WHERE c.assessment_id = %s
        ORDER BY c.id, b.id
        """,
        (assessment_id,),
    )
    criteria: dict[int, Row] = {}
    for r in rows:
        cid = r["criterion_id"]
        if cid not in criteria:
            criteria[cid] = {
                "name": r["name"],
                "description": r["description"],
                "weighting_percent": r["weighting_percent"],
                "grade_bands": [],
            }
        if r["band_name"] is not None or r["descriptor"] is not None:
            criteria[cid]["grade_bands"].append(
                {"band_name": r["band_name"], "descriptor": r["descriptor"]}
            )
    return list(criteria.values())


def get_grade_scale() -> list[Row]:
    """The seeded university scale (band name, mark range, UG/PG outcome)."""
    return _fetch_all("SELECT * FROM grade_scale ORDER BY max_mark DESC")


# ---------- everything for one assessment ----------

def get_full_assessment(assessment_id: int) -> dict[str, Any]:
    """One dict with facts, text sections, outcomes, checklist and criteria."""
    return {
        "facts": get_assessment(assessment_id),
        "text": get_text_fields(assessment_id),
        "learning_outcomes": get_learning_outcomes(assessment_id),
        "submission_checklist": get_submission_checklist(assessment_id),
        "criteria": get_criteria(assessment_id),
    }


if __name__ == "__main__":
    # Quick test: python db.py
    assessments = list_assessments()
    print(f"{len(assessments)} assessment(s) in the database")
    for a in assessments:
        print(a)
    if assessments:
        first = assessments[0]["id"]
        print("\nFacts for first assessment:")
        print(get_assessment(first))
        print("\nCriteria count:", len(get_criteria(first)))
        print("Learning outcomes:", len(get_learning_outcomes(first)))
        print("Text sections filled:", list(get_text_fields(first).keys()))