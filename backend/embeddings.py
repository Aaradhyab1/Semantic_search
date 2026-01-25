from sentence_transformers import SentenceTransformer
import numpy as np
import logging

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"         # Produces sentence or paragraph embeddings of 384 dimensions

# Trying to load the model. If it fails, the server will not start.

try:
    _model = SentenceTransformer(MODEL_NAME)
except Exception:
    logger.exception("Failed to load embedding model")
    raise

# embed function coverts chunk from the file into a numpy array of numerical vectors

def embed_texts(texts: list[str]) -> np.ndarray:
    return _model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

# embed_query function converts a query entered by the user into a numpy array of numerical vectors

def embed_query(query: str) -> np.ndarray:
    return _model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )
