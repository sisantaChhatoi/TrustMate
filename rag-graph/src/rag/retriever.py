"""Retrieves relevant fraud-knowledge chunks for a user message.

Embeds the query with bge-m3 and searches the FAISS index built by
ingest.py. The query is never translated — bge-m3's cross-lingual embedding
space lets a Hindi/Hinglish question retrieve English-language knowledge-
base chunks (and vice versa) directly.
"""

from __future__ import annotations

from pathlib import Path

from src.rag.embedder import embed
from src.rag.vector_store import VectorStore

INDEX_DIR = Path(__file__).resolve().parents[2] / "data" / "rag"

# Short/low-signal messages (e.g. a one-word answer like "SBI") score in the
# same weak range as genuine noise -- below this, the match isn't meaningful
# enough to inject as context, and just dilutes the model's attention on the
# actual conversation.
MIN_RELEVANCE_SCORE = 0.35

_store: VectorStore | None = None


def _get_store() -> VectorStore:
    global _store
    if _store is None:
        if not (INDEX_DIR / "index.faiss").exists():
            raise RuntimeError(
                f"No FAISS index found at {INDEX_DIR}. Run `python -m src.rag.ingest` first."
            )
        _store = VectorStore()
        _store.load(INDEX_DIR)
    return _store


def retrieve(query: str, k: int = 4) -> list[str]:
    """Returns up to k relevant chunk texts (each prefixed with its source
    filename), filtering out matches too weak to be meaningfully relevant."""
    store = _get_store()
    query_vector = embed([query])[0]
    results = store.search(query_vector, k=k)
    return [
        f"(source: {r['source']}) {r['text']}"
        for r in results
        if r["score"] >= MIN_RELEVANCE_SCORE
    ]
