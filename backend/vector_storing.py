import faiss
import os
import pickle
import logging
from .embeddings import embed_query

logger = logging.getLogger(__name__)

FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "data/faiss.index")
# New path for the metadata (text chunks + filenames)
METADATA_PATH = os.getenv("METADATA_PATH", "data/faiss_metadata.pkl")

os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)

class VectorStore:
    def __init__(self):
        self.index = None
        self.metadata = []  # Stores [{"text": "...", "source": "filename.pdf"}, ...]
        self._load_index()

    def _load_index(self):
        # 1. Load the FAISS vector index
        if os.path.exists(FAISS_INDEX_PATH):
            try:
                self.index = faiss.read_index(FAISS_INDEX_PATH)
                logger.info("FAISS index loaded from disk")
            except Exception:
                logger.exception("Failed to load FAISS index")
                self.index = None

        # 2. Load the associated metadata (text + sources)
        if os.path.exists(METADATA_PATH):
            try:
                with open(METADATA_PATH, "rb") as f:
                    self.metadata = pickle.load(f)
                logger.info("Metadata loaded from disk")
            except Exception:
                logger.exception("Failed to load metadata")
                self.metadata = []

    def _save_index(self):
        # Save the vectors
        if self.index is not None:
            faiss.write_index(self.index, FAISS_INDEX_PATH)
        # Save the metadata using pickle
        with open(METADATA_PATH, "wb") as f:
            pickle.dump(self.metadata, f)

    def add(self, chunks: list[str], embeddings, filename: str):
        if not chunks:
            return

        dim = embeddings.shape[1]
        if self.index is None:
            # Using Inner Product (IP) similarity
            self.index = faiss.IndexFlatIP(dim)

        self.index.add(embeddings)
        
        # Link each chunk to its source filename
        for chunk in chunks:
            self.metadata.append({
                "text": chunk,
                "source": filename
            })
        
        self._save_index()

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if self.index is None:
            return []

        query_vec = embed_query(query)
        scores, indices = self.index.search(query_vec, top_k)

        results = []
        for idx in indices[0]:
            if 0 <= idx < len(self.metadata):
                results.append(self.metadata[idx]) # Returns {"text": ..., "source": ...}

        return results

vector_store = VectorStore()