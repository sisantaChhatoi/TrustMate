# RAG fraud-chat

See the [root README](../../README.md) for the full system picture. This
covers `src/rag/` specifically.

## Chunking (`ingest.py`)

Each `knowledge_base/*.md` file is split on blank lines into paragraphs,
then paragraphs are greedily packed into chunks targeting ~350 tokens
(approximated as `len(text) // 4`), with a ~500 token ceiling. A single
paragraph longer than the ceiling is kept whole rather than split
mid-sentence. No overlap between chunks at this knowledge-base size.

## Adding to the knowledge base

Drop a new `.md` file into `knowledge_base/`, then rebuild the index:
```
python -m src.rag.ingest
```
No special frontmatter needed — write it like a normal advisory document:
`##` headers per topic, blank-line-separated paragraphs. Look at the
existing files for the expected tone (calm, factual, ends with what to
actually do).

## How a reply gets built (`chat.py`)

1. `retrieve(user_message)` — embed the message, search FAISS, drop
   matches below a relevance floor (a one-word answer like "SBI" shouldn't
   drag in unrelated chunks about lottery scams).
2. `incident.next_missing_field()` picks the single next graph-relevant
   field to gently ask about — at most once per field, ever (see below).
3. The system + retrieved context + that one nudge get sent to Sarvam.
4. A repetition guard checks the draft against the last few assistant
   turns; if it's a near-repeat (a known failure mode of the underlying
   model over long conversations), it retries once, then falls back to a
   plain templated reply as a last resort.
5. A *separate* background call extracts structured fields from the full
   transcript and merges them into the session's `Incident` — this never
   blocks the reply that already went back to the user.

## Why "ask each field once" (`incident.py`)

Earlier versions kept re-nudging a field every turn until it was filled,
which produced exactly the repeated-question loops you'd expect once the
underlying model didn't reliably follow the nudge. `next_missing_field()`
now marks a field "asked" the moment the question is actually shown (not
swallowed by the repetition-guard's generic fallback), and never asks it
again — answered or not. Extraction still picks up a late answer from the
transcript regardless; only the *prompt to ask* is one-shot.

The one deliberate exception: `mule_account` gets a single bounded
follow-up if the user only gave a bank name ("SBI"), not the actual account
number — that's finishing the same question, not asking a new one.

## Testing manually

```
python -m src.rag.ask              # interactive, keeps memory, fresh session each run
python -m src.rag.ask "message"    # one-shot
python -m src.rag.ask --stream "message"   # see it stream token by token
```
