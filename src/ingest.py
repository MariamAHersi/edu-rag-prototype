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
from schema import AssessmentBrief


#%%
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

# %%
load_dotenv()

def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(len(doc)):
        page = doc[i]
        pages.append(f"[PAGE {i + 1}]\n{page.get_text()}")
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
            if response.text is None:
                raise ValueError("Gemini returned no response text")
            
            return AssessmentBrief.model_validate_json(response.text)
        
        except errors.ServerError as e:
            wait = 2 ** attempt * 5   
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
        user="root",  
        password=os.environ["MYSQL_PASSWORD"],  
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
        row = cur.fetchone()

        if row is None:
            raise ValueError(f"No assessment saved for {source_file}")

        assessment_id = row[0]

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


