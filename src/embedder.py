#%%
import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer


#%%

### Step 4 Python Code: `embedder.py`
# This script takes `chunks.json` from Step 3, builds normalised vector embeddings, saves them to disk, and includes a lightweight `retrieve()` function for semantic similarity search.
CHUNKS_FILE = Path("../briefs/chunks.json")
VECTOR_INDEX_FILE = Path("../briefs/vector_index.json")
EMBEDDINGS_FILE = Path("../briefs/embeddings.npy")

class SimpleVectorStore:

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Initializes the embedding model.
        print(f"Loading embedding model '{model_name}'...")
        self.model = SentenceTransformer(model_name)
        self.chunks = []
        self.embeddings = None

    def build_index(
        self, chunks_path: Path, save_dir: Path = Path("../briefs")
    ):
        # Generates normalized vector embeddings for all chunks and saves index.
        raw_chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        self.chunks = raw_chunks

        # Extract content text for embedding
        texts = [c["content"] for c in self.chunks]

        print(
            f"Generating embeddings for {len(texts)} chunks using {self.model}..."
        )
        # normalise_embeddings = True allows dot product to equal cosine similarity
        embeddings_matrix = self.model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        self.embeddings = embeddings_matrix

        # Save artifacts to disk
        np.save(EMBEDDINGS_FILE, self.embeddings)
        VECTOR_INDEX_FILE.write_text(
            json.dumps(self.chunks, indent=2), encoding="utf-8"
        )
        print(
            f"Index successfully built! Saved {self.embeddings.shape} matrix to {EMBEDDINGS_FILE}"
        )

    def load_index(self):
        # Loads pre-computed embeddings and chunk metadata from disk.
        if not EMBEDDINGS_FILE.exists() or not VECTOR_INDEX_FILE.exists():
            raise FileNotFoundError("Index files not found. Run build_index() first.")

        self.chunks = json.loads(
            VECTOR_INDEX_FILE.read_text(encoding="utf-8")
        )
        self.embeddings = np.load(EMBEDDINGS_FILE)
        print(
            f"Loaded index with {len(self.chunks)} chunks and embeddings shape {self.embeddings.shape}."
        )

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        # Performs cosine similarity search using NumPy dot product.
        if self.embeddings is None:
            self.load_index()

        embeddings = self.embeddings
        assert embeddings is not None, "Embeddings failed to load"

        # Encode query and normalize vector
        query_embedding = self.model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        )

        # Dot product between normalized vectors == Cosine Similarity score
        scores = np.dot(embeddings, query_embedding.T).flatten()

        # Get top-K indices sorted by score descending
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            match = dict(self.chunks[idx])
            match["similarity_score"] = float(round(scores[idx], 4))
            results.append(match)

        return results

def main():
    store = SimpleVectorStore()

    # 1. Build & save the index from Step 3 chunks
    store.build_index(CHUNKS_FILE)

    # 2. Test semantic search retrieval
    test_query = "What are the requirements and learning outcomes for the database design assessment?"
    print(f"\n--- Testing Query: '{test_query}' ---")

    matches = store.retrieve(test_query, top_k=3)
    for i, res in enumerate(matches, start=1):
        print(f"\n[Match {i}] Score: {res['similarity_score']}")
        print(f"Source: {res['source_file']} | Section: {res['section']}")
        print(f"Content Snippet: {res['content'][:200]}...")

if __name__ == "__main__":
    main()

