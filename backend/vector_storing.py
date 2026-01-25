import faiss
import os
import logging
from .embeddings import embed_query
logger = logging.getLogger(__name__)

FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "data/faiss.index")
os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)


class VectorStore:
    def __init__(self):
        self.index = None
        self.text_chunks = []
        self._load_index()              # Loading existing FAISS index from the local disk

    def _load_index(self):
        if os.path.exists(FAISS_INDEX_PATH):        # checking if the index file exists
            try:
                self.index = faiss.read_index(FAISS_INDEX_PATH)     # loading the index if found
                logger.info("FAISS index loaded from disk")
            except Exception:
                logger.exception("Failed to load FAISS index")      # raising an exception if loading fails and refreshing
                self.index = None

    def _save_index(self):
        if self.index is not None:
            faiss.write_index(self.index, FAISS_INDEX_PATH)     # saves vectors after every update

    def add(self, chunks: list[str], embeddings):
        if not chunks:      # making sure there are no empty chunks
            return

        dim = embeddings.shape[1]

        if self.index is None:          # Creates a new FAISS index if it doesn't exist. Uses inner product similarity
            self.index = faiss.IndexFlatIP(dim)

        self.index.add(embeddings)      # adding vectors to FAISS
        self.text_chunks.extend(chunks)     # adding text in the same order
        self._save_index()      #

    def search(self, query: str, top_k: int = 5) -> list[str]:
        if self.index is None:
            return []

        query_vec = embed_query(query)
        scores, indices = self.index.search(query_vec, top_k)

        results = []
        for idx in indices[0]:
            if 0 <= idx < len(self.text_chunks):
                results.append(self.text_chunks[idx])

        return results


# Singleton instance (shared across API workers)

vector_store = VectorStore()