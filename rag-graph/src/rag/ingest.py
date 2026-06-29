"""Builds the FAISS index from src/rag/knowledge_base/*.md|*.txt.

Run once (and again whenever the knowledge base changes):
    python -m src.rag.ingest

Chunking: each file is split into paragraphs on blank lines, then paragraphs
are greedily packed into chunks targeting ~350 tokens (approximated as
len(text) // 4 chars-per-token) with a ~500 token ceiling. A single paragraph
longer than the ceiling is kept whole rather than split mid-sentence.
"""

from __future__ import annotations

from pathlib import Path

from src.rag.embedder import embed
from src.rag.vector_store import VectorStore

KB_DIR = Path(__file__).parent / "knowledge_base"
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "rag"

TARGET_TOKENS = 350
MAX_TOKENS = 500
CHARS_PER_TOKEN = 4


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _chunk_file(path: Path) -> list[dict]:
    paragraphs = _paragraphs(path.read_text(encoding="utf-8"))
    chunks: list[dict] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        if current:
            chunks.append(
                {
                    "text": "\n\n".join(current),
                    "source": path.name,
                    "chunk_index": len(chunks),
                }
            )

    for para in paragraphs:
        para_tokens = len(para) // CHARS_PER_TOKEN
        if current and current_len + para_tokens > TARGET_TOKENS:
            flush()
            current, current_len = [], 0
        current.append(para)
        current_len += para_tokens
        if current_len > MAX_TOKENS:
            flush()
            current, current_len = [], 0
    flush()
    return chunks


def ingest() -> None:
    files = sorted(KB_DIR.glob("*.md")) + sorted(KB_DIR.glob("*.txt"))
    if not files:
        raise RuntimeError(f"No .md/.txt files found in {KB_DIR}")

    chunks: list[dict] = []
    for path in files:
        chunks.extend(_chunk_file(path))

    print(f"Chunked {len(files)} file(s) into {len(chunks)} chunk(s).")
    vectors = embed([c["text"] for c in chunks])

    store = VectorStore()
    store.build(vectors, chunks)
    store.save(OUT_DIR)
    print(f"Saved FAISS index to {OUT_DIR}")


if __name__ == "__main__":
    ingest()
