#%%
import sys
import os
import fitz
import time
from google.genai import errors
from google import genai
from google.genai import types
from pydantic import ValidationError
from dotenv import load_dotenv
import mysql.connector
from pathlib import Path

# %%
load_dotenv()

def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc, start=1):
        pages.append(f"[PAGE {i}]\n{page.get_text()}")
    return "\n\n".join(pages)

def extract_brief(text, max_attempts=6):
    client = genai.Client()
    prompt = (
        "Extract the assessment brief details from the document below. "
        "Only use information stated in the document. "
        "Use null for anything not stated. Do not guess.\n\n"
        f"DOCUMENT:\n{text}"
    )

    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AssessmentBrief,
                ),
            )
            return AssessmentBrief.model_validate_json(response.text)
        except errors.ServerError as e:
            wait = 2 ** attempt * 5   # 5, 10, 20, 40, 80, 160 seconds
            print(f"Server error {e.code}, retrying in {wait}s (attempt {attempt + 1}/{max_attempts})")
            time.sleep(wait)

    raise RuntimeError("Gemini still unavailable after several attempts")
    
if __name__ == "__main__":
    pdf_path = "sample_pdf.pdf"
    text = extract_text(pdf_path)

    print("=== RAW TEXT (first 1500 chars) ===")
    print(text[:1500])

    try:
        brief = extract_brief(text)
    except ValidationError as e:
        print("\n=== VALIDATION FAILED ===")
        print(e)
        sys.exit(1)

    print("\n=== EXTRACTED ===")
    print(brief.model_dump_json(indent=2))


# %%
def extract_images(pdf_path, out_root="extracted_images", min_size=100):
    """Save meaningful images from a PDF and return a record of each one."""
    pdf_path = Path(pdf_path)
    out_dir = Path(out_root) / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    seen_xrefs = set()
    results = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1

        for image_index, img in enumerate(page.get_images(full=True), start=1):
            xref = img[0]
            if xref in seen_xrefs:
                continue  # same image repeated (e.g. logo in a header)
            seen_xrefs.add(xref)

            base = doc.extract_image(xref)
            if base["width"] < min_size or base["height"] < min_size:
                continue  # probably an icon or decoration

            image_path = out_dir / f"page{page_number}_img{image_index}.{base['ext']}"
            image_path.write_bytes(base["image"])

            results.append({
                "source_file": pdf_path.name,
                "page_number": page_number,
                "image_path": str(image_path),
                "width": base["width"],
                "height": base["height"],
            })

    print(f"{pdf_path.name}: saved {len(results)} images")
    return results

# %%
MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}

def describe_image(image_path):
    ext = Path(image_path).suffix.lstrip(".").lower()
    if ext not in MIME:
        return None  # unsupported format, skip for now

    client = genai.Client()
    prompt = (
        "This image comes from a university assessment brief. Describe only what is visible. "
        "Transcribe any text in it. If it is an example, diagram or screenshot, "
        "explain what it shows. If it is purely decorative (logo, banner, icon), "
        "reply with exactly: DECORATIVE"
    )
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=Path(image_path).read_bytes(), mime_type=MIME[ext]),
            prompt,
        ],
    )
    return response.text.strip()

# %%
load_dotenv()

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password=os.environ["MYSQL_PASSWORD"],
    database="rag_system",
)

print("Connected successfully!")

conn.close()

# %%
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",  # or your own MySQL user
        password=os.environ["MYSQL_PASSWORD"],  # don't hard-code it
        database="rag_system",
    )

# %%
def save_brief(brief, source_file):
    data = {
        "source_file": source_file,
        **brief.model_dump(exclude={"learning_outcomes", "marking_criteria", "requirements","submission_checklist"}),
    }

    columns = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    updates = ", ".join(
        f"{col}=VALUES({col})" for col in data if col != "source_file"
    )

    sql = f"""
        INSERT INTO assessments ({columns})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE {updates}
    """

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, list(data.values()))
        conn.commit()
    finally:
        conn.close()

# %%
def save_list_items(table, assessment_id, items):
    conn = get_connection()
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

# %%
def get_assessment_id(source_file):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM assessments WHERE source_file = %s", (source_file,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"No assessment saved for {source_file}")
        return row[0]
    finally:
        conn.close()

# %%
def save_rubric(brief, source_file):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM assessments WHERE source_file = %s", (source_file,))
        assessment_id = cur.fetchone()[0]

        # clear old rubric so re-running doesn't duplicate rows
        cur.execute("DELETE FROM criteria WHERE assessment_id = %s", (assessment_id,))

        for c in brief.marking_criteria:
            cur.execute(
                "INSERT INTO criteria (assessment_id, name, description, weighting_percent) VALUES (%s, %s, %s, %s)",
                (assessment_id, c.name, c.description, c.weighting_percent),
            )
            criterion_id = cur.lastrowid
            for b in c.grade_bands:
                cur.execute(
                    "INSERT INTO grade_bands (criterion_id, band_name, descriptor) VALUES (%s, %s, %s)",
                    (criterion_id, b.band_name, b.descriptor),
                )
        conn.commit()
    finally:
        conn.close()

# %%
MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}

def describe_image(image_path):
    ext = Path(image_path).suffix.lstrip(".").lower()
    if ext not in MIME:
        return None  # unsupported format, skip for now

    client = genai.Client()
    prompt = (
        "This image comes from a university assessment brief. Describe only what is visible. "
        "Transcribe any text in it. If it is an example, diagram or screenshot, "
        "explain what it shows. If it is purely decorative (logo, banner, icon), "
        "reply with exactly: DECORATIVE"
    )
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=Path(image_path).read_bytes(), mime_type=MIME[ext]),
            prompt,
        ],
    )
    return response.text.strip()

# %%
def save_images(source_file, image_records):
    assessment_id = get_assessment_id(source_file)  # same helper you already have
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM task_images WHERE assessment_id = %s", (assessment_id,))
        for rec in image_records:
            description = describe_image(rec["image_path"])
            if description is None or description == "DECORATIVE":
                continue
            cur.execute(
                "INSERT INTO task_images (assessment_id, page_number, image_path, description) "
                "VALUES (%s, %s, %s, %s)",
                (assessment_id, rec["page_number"], rec["image_path"], description),
            )
        conn.commit()
    finally:
        conn.close()

# %%
brief = extract_brief(text)

# %%
save_brief(brief, "my_brief.pdf")    

# %%
cur_id = get_assessment_id("my_brief.pdf") 

# %%
save_list_items("learning_outcomes", cur_id, brief.learning_outcomes)

# %%
save_rubric(brief, "my_brief.pdf")

# %%
pdf_path = "sample_pdf.pdf"
filename = "my_brief.pdf" 
images = extract_images(pdf_path)
save_images(filename, images)

