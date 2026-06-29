"""Multilingual text embedding via paraphrase-multilingual-MiniLM-L12-v2.

Supports 50+ languages including Hindi and Hinglish, and runs on CPU. Chosen
over BAAI/bge-m3 (2.2GB) for a much smaller download (~470MB) at the cost of
some retrieval quality on heavily code-mixed text. Sarvam has no embeddings
API, which is why this uses a local HuggingFace model instead.

The model is loaded once at module import and reused.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_model = SentenceTransformer(MODEL_NAME, device="cpu")


def embed(texts: list[str]) -> np.ndarray:
    """Embeds a list of texts into normalized vectors (cosine via dot product)."""
    return _model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
