#%%
#Step 1: import neccessary files 
import json
import pathlib
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
import pdfplumber

#%%
RAW_DIR = pathlib.Path("../../briefs/raw_docs")
OUT_DIR = pathlib.Path("../../briefs/extracted_docs")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def iter_docx_blocks(doc):
#Yields paragraphs and tables in their exact document reading order."""
    for child in doc.element.body:
        if child.tag.endswith("p"):
            yield Paragraph(child, doc)
        elif child.tag.endswith("tbl"):
            yield Table(child, doc)


def format_complex_docx_table(table: Table) -> str:
#Extracts DOCX tables while handling merged cells and side-by-side columns."""
    rows_data = []

    for row in table.rows:
        row_cells = []
        seen_cells = set()

        for cell in row.cells:
            cell_id = id(cell._tc)

            if cell_id not in seen_cells:
                seen_cells.add(cell_id)

                cell_text = cell.text.strip().replace("\n", " <br> ")
                row_cells.append(cell_text if cell_text else "-")

        if any(c != "-" for c in row_cells):
            rows_data.append(row_cells)

    if not rows_data:
        return ""

    md_lines = []

    header = rows_data[0]

    md_lines.append("| " + " | ".join(header) + " |")
    md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    for row in rows_data[1:]:
        if len(row) < len(header):
            row += ["-"] * (len(header) - len(row))
        elif len(row) > len(header):
            row = row[:len(header)]

        md_lines.append("| " + " | ".join(row) + " |")

    return "\n".join(md_lines)


def extract_docx(path: pathlib.Path) -> str:
#Extracts DOCX text while preserving paragraphs and tables."""
    doc = Document(str(path))
    parts = []

    for block in iter_docx_blocks(doc):

        if isinstance(block, Paragraph):
            text = block.text.strip()

            if text:
                parts.append(text)

        elif isinstance(block, Table):
            table_md = format_complex_docx_table(block)

            if table_md:
                parts.append(f"\n{table_md}\n")

    return "\n\n".join(parts)


def extract_pdf(path: pathlib.Path) -> str:
#Extracts PDF text and structured tables."""
    output_parts = []

    with pdfplumber.open(path) as pdf:

        for page_num, page in enumerate(pdf.pages, start=1):

            output_parts.append(f"--- Page {page_num} ---")

            # Try to detect structured tables
            tables = page.extract_tables()

            if tables:

                for table in tables:

                    md_table_lines = []

                    for row_idx, row in enumerate(table):

                        clean_row = [
                            cell.replace("\n", " ").strip()
                            if cell
                            else "-"
                            for cell in row
                        ]

                        md_table_lines.append(
                            "| " + " | ".join(clean_row) + " |"
                        )

                        if row_idx == 0:
                            md_table_lines.append(
                                "| "
                                + " | ".join(["---"] * len(clean_row))
                                + " |"
                            )

                    output_parts.append("\n".join(md_table_lines))

            else:
                # If no table is detected, extract normal page text
                page_text = page.extract_text(layout=True) or ""

                if page_text.strip():
                    output_parts.append(page_text)

    return "\n\n".join(output_parts)


def main():
    manifest = []

    for path in sorted(RAW_DIR.iterdir()):

        suffix = path.suffix.lower()

        if suffix == ".pdf":
            text = extract_pdf(path)

        elif suffix == ".docx":
            text = extract_docx(path)

        else:
            print(f"Skipping unsupported file type: {path.name}")
            continue

        out_path = OUT_DIR / f"{path.stem}.txt"

        out_path.write_text(text, encoding="utf-8")

        manifest.append(
            {
                "source_file": path.name,
                "extracted_file": out_path.name,
                "char_count": len(text),
                "word_count": len(text.split()),
            }
        )

        print(
            f"Extracted {path.name} -> "
            f"{out_path.name} ({len(text)} chars)"
        )

    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    print(f"\nExtraction complete. Output saved to {OUT_DIR}")


if __name__ == "__main__":
    main()