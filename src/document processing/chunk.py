#%%
import json
import re
from pathlib import Path

#%%
EXTRACTED_DIR = Path("../../briefs/extracted_docs")
CHUNKS_OUT = Path("../../briefs/chunks.json")

def is_table(text_block: str) -> bool:
    """Checks if a text block is a Markdown table."""
    return "|" in text_block and "---" in text_block

def chunk_document(
    file_path: Path, max_chunk_size: int = 800, overlap: int = 100
) -> list[dict]:
    """Splits extracted assessment briefs into metadata-rich semantic chunks."""
    raw_text = file_path.read_text(encoding="utf-8")

    # Split document into logical sections using headers or double linebreaks
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]

    chunks = []
    current_section = "General / Overview"
    current_buffer = ""
    chunk_id = 1

    for block in paragraphs:
        # Detect section headers (e.g., '1. Learning Outcomes', '## Rubric', 'Assessment Task')
        header_match = re.match(
            r"^(#+|\d+\.\s+|[A-Z\s]{4,}:)(.+)", block, re.MULTILINE
        )
        if header_match and not is_table(block):
            current_section = block.strip("#").strip()

        # Rule 1: Tables stay as standalone chunks to prevent row splitting
        if is_table(block):
            # Flush any accumulated text buffer first
            if current_buffer.strip():
                chunks.append(
                    {
                        "chunk_id": f"{file_path.stem}_chunk_{chunk_id}",
                        "source_file": file_path.name,
                        "section": current_section,
                        "content": current_buffer.strip(),
                        "is_table": False,
                    }
                )
                chunk_id += 1
                current_buffer = ""

            # Save the table as its own dedicated chunk
            chunks.append(
                {
                    "chunk_id": f"{file_path.stem}_chunk_{chunk_id}",
                    "source_file": file_path.name,
                    "section": current_section,
                    "content": block,
                    "is_table": True,
                }
            )
            chunk_id += 1
            continue

        # Rule 2: Combine standard text paragraphs up to max_chunk_size
        if len(current_buffer) + len(block) < max_chunk_size:
            current_buffer += "\n\n" + block if current_buffer else block
        else:
            # Chunk limit reached — store current chunk
            if current_buffer.strip():
                chunks.append(
                    {
                        "chunk_id": f"{file_path.stem}_chunk_{chunk_id}",
                        "source_file": file_path.name,
                        "section": current_section,
                        "content": current_buffer.strip(),
                        "is_table": False,
                    }
                )
                chunk_id += 1

            # Start new buffer with overlap
            overlap_text = (
                current_buffer[-overlap:]
                if len(current_buffer) > overlap
                else ""
            )
            current_buffer = (
                (overlap_text + "\n\n" + block) if overlap_text else block
            )

    # Flush remaining text
    if current_buffer.strip():
        chunks.append(
            {
                "chunk_id": f"{file_path.stem}_chunk_{chunk_id}",
                "source_file": file_path.name,
                "section": current_section,
                "content": current_buffer.strip(),
                "is_table": False,
            }
        )

    return chunks

def main():
    all_chunks = []
    for txt_file in sorted(EXTRACTED_DIR.glob("*.txt")):
        if txt_file.name == "manifest.json":
            continue
        file_chunks = chunk_document(txt_file)
        all_chunks.extend(file_chunks)
        print(f"{txt_file.name}: Created {len(file_chunks)} chunks")

    CHUNKS_OUT.write_text(json.dumps(all_chunks, indent=2), encoding="utf-8")
    print(
        f"\nChunking complete. Total {len(all_chunks)} chunks saved to {CHUNKS_OUT}"
    )

if __name__ == "__main__":
    main()