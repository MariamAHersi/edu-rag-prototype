
import hashlib
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

import chunking

MODEL_NAME = "all-MiniLM-L6-v2"

INDEX_DIR = Path(__file__).parent / "index"
EMBEDDINGS_FILE = INDEX_DIR / "embeddings.npy"
CHUNKS_FILE = INDEX_DIR / "chunks.json"
FINGERPRINT_FILE = INDEX_DIR / "fingerprint.txt"


def embed_text(chunk: dict) -> str:
    """What actually gets embedded: the section name and module give the text context."""
    title = chunk.get("module_title") or chunk.get("module_code") or ""
    field = chunk["field"].replace("_", " ")
    return f"{title} - {field}\n{chunk['content']}"


def fingerprint(chunks: list[dict], model_name: str) -> str:
    """A hash of everything that affects the index, to detect when it is out of date."""
    h = hashlib.sha256(model_name.encode("utf-8"))
    for c in chunks:
        h.update(c["chunk_id"].encode("utf-8"))
        h.update(embed_text(c).encode("utf-8"))
    return h.hexdigest()


class SimpleVectorStore:
    def __init__(self, model_name: str = MODEL_NAME):
        print(f"Loading embedding model '{model_name}'...")
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.chunks: list[dict] = []
        self.embeddings: np.ndarray | None = None

    # ---------- building and loading ----------

    def build_index(self, chunks: list[dict]) -> None:
        """Embed all chunks and save the index to disk."""
        self.chunks = chunks
        if chunks:
            matrix = self.model.encode(
                [embed_text(c) for c in chunks],
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,  # dot product == cosine similarity
            )
        else:
            dim = self.model.get_sentence_embedding_dimension() or 384
            matrix = np.zeros((0, dim), dtype=np.float32)
        self.embeddings = matrix

        INDEX_DIR.mkdir(exist_ok=True)
        np.save(EMBEDDINGS_FILE, matrix)
        CHUNKS_FILE.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
        FINGERPRINT_FILE.write_text(fingerprint(chunks, self.model_name), encoding="utf-8")
        print(f"Index built: {len(chunks)} chunks, matrix shape {matrix.shape}")

    def load_index(self) -> None:
        self.chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
        self.embeddings = np.load(EMBEDDINGS_FILE)
        print(f"Loaded index: {len(self.chunks)} chunks")

    def ensure_index(self, force: bool = False) -> None:
        """Load the saved index if it still matches the database, otherwise rebuild it."""
        chunks = chunking.build_all_chunks()
        current = fingerprint(chunks, self.model_name)

        files_exist = (
            EMBEDDINGS_FILE.exists() and CHUNKS_FILE.exists() and FINGERPRINT_FILE.exists()
        )
        up_to_date = files_exist and FINGERPRINT_FILE.read_text(encoding="utf-8") == current

        if up_to_date and not force:
            self.load_index()
        else:
            self.build_index(chunks)

    # ---------- searching ----------

    def retrieve(self, query: str, assessment_id: int, top_k: int = 4) -> list[dict]:
        """Top matching chunks for one assessment, best first, each with a similarity_score."""
        if self.embeddings is None:
            self.ensure_index()
        assert self.embeddings is not None

        rows = [i for i, c in enumerate(self.chunks) if c["assessment_id"] == assessment_id]
        if not rows:
            return []

        query_vec = self.model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        )
        scores = np.dot(self.embeddings[rows], query_vec.T).flatten()
        best = np.argsort(scores)[::-1][:top_k]

        results = []
        for j in best:
            match = dict(self.chunks[rows[j]])
            match["similarity_score"] = float(round(scores[j], 4))
            results.append(match)
        return results


if __name__ == "__main__":
    # Quick test: python embedding.py
    import db

    store = SimpleVectorStore()
    store.ensure_index()
    assessments = db.list_assessments()
    if assessments:
        first = assessments[0]["id"]
        for q in ["Am I allowed to use AI?", "What does the task ask me to do?"]:
            print(f"\n--- {q} ---")
            for r in store.retrieve(q, first, top_k=3):
                print(f"[{r['similarity_score']}] {r['field']}: {r['content'][:150]}...")