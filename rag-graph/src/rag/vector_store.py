"""FAISS-backed vector store for the fraud knowledge base.

Uses a flat inner-product index (IndexFlatIP) over normalized embeddings,
i.e. exact cosine similarity search. The knowledge base is small (dozens to
low hundreds of chunks), so an approximate index would add complexity for no
real speed benefit. Chunk texts/metadata live in a sidecar JSON file next to
the FAISS index since FAISS only stores vectors.
"""

from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

INDEX_FILENAME = "index.faiss"
CHUNKS_FILENAME = "chunks.json"


class VectorStore:
    def __init__(self) -> None:
        self.index: faiss.Index | None = None
        self.chunks: list[dict] = []

    def build(self, vectors: np.ndarray, chunks: list[dict]) -> None:
        """chunks[i] (a dict with at least 'text' and 'source') corresponds to vectors[i]."""
        dim = vectors.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(vectors)
        self.index = index
        self.chunks = chunks

    def save(self, directory: str | Path) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(directory / INDEX_FILENAME))
        (directory / CHUNKS_FILENAME).write_text(
            json.dumps(self.chunks, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load(self, directory: str | Path) -> None:
        directory = Path(directory)
        self.index = faiss.read_index(str(directory / INDEX_FILENAME))
        self.chunks = json.loads((directory / CHUNKS_FILENAME).read_text(encoding="utf-8"))

    def search(self, query_vector: np.ndarray, k: int = 4) -> list[dict]:
        """Returns up to k chunks as {text, source, chunk_index, score}, best first."""
        if self.index is None:
            raise RuntimeError("Vector store is empty — call build() or load() first.")
        query_vector = np.asarray(query_vector).reshape(1, -1)
        scores, indices = self.index.search(query_vector, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append({**self.chunks[idx], "score": float(score)})
        return results
