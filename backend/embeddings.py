from sentence_transformers import SentenceTransformer
import numpy as np
import logging

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"         

try:
    _model = SentenceTransformer(MODEL_NAME)
except Exception:
    logger.exception("Failed to load embedding model")
    raise

def embed_texts(texts: list[str]) -> np.ndarray:
    return _model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    )


def embed_query(query: str) -> np.ndarray:
    return _model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )
