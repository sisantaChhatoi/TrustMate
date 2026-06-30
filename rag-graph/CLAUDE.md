# RAG Fraud-Chat & Fraud-Graph Intelligence

Context file for Claude Code. Lives at the root of `rag-graph/` once merged
into the main `cybersec-agent` repo (this folder is currently developed in
its own repo and pushed into `cybersec-agent`'s `rag_chat` branch as a
self-contained `rag-graph/` subfolder).

## Code style

- Clean, PEP 8 / PEP 20 code. Type-annotate signatures.
- **Minimal comments.** No verbose docstrings. Comment only non-obvious
  *why* (a workaround, an invariant, a known model failure mode it's
  guarding against) — not *what*. Let names carry intent.

## What this is

Two coupled pieces:
1. **`src/rag/`** — a multilingual chat assistant (Hindi/Hinglish/English).
   Someone describes a suspicious call/message, gets a grounded,
   in-language risk verdict, while the system quietly extracts the
   structured details (caller number, mule account/UPI, amount, region)
   that matter for tracing the scam network behind it.
2. **`src/graph/`** — turns those extracted incidents into a fraud network
   graph (NetworkX local + Neo4j Aura) that surfaces reused mule
   accounts/UPI handles, fraud rings (Louvain community detection),
   multi-region operations, and investigative-support evidence reports.

This is **not currently wired into the main app or backend** (`app/`,
`backend/server`). It was built and tested standalone via a CLI
(`python -m src.rag.ask`). See "Integrating into the real app" below for
exactly what that takes.

## Architecture

```
User chats (Hindi / Hinglish / English)
        |
        v
src/rag/   RAG chat: multilingual embeddings + FAISS retrieval over a fraud
        |  knowledge base -> Sarvam-30B generates a grounded, in-language
        |  reply -> a background pass extracts structured fields one at a
        |  time (each graph-relevant field is asked at most once, ever).
        |  At most one extraction worker runs per session (coalescing worker
        |  pattern) -- fast typing never queues up a backlog of threads.
        v
MongoDB: <db>.incidents  <- source of truth (currently a separate Atlas
        |  cluster, see "Integrating" below for why that needs to change)
        |
        | every save triggers THREE best-effort background syncs:
        |   1. Neo4j -- idempotent graph update for this incident
        |   2. Geospatial -- rebuilds hotspots/heatmap/deployment ranking
        |      from all incidents so the map is always current
        |
        | python -m src.graph.neo4j_run / geospatial_run are only needed
        | for a full on-demand rebuild or to get the human-readable summary
        v
src/graph/  fraud network graph (NetworkX + Neo4j Aura) AND geospatial
        |   intelligence:
        |     - local: in-memory NetworkX + Louvain community detection
        |     - Neo4j Aura: Cypher pattern queries (GDS not available on
        |       free tier -- Louvain runs in NetworkX)
        |     - geospatial: Nominatim geocoding (cached), fraud hotspot
        |       aggregation, NCRB baseline overlay, patrol deployment ranking
        v
Fraud rings, reused/high-risk accounts, jurisdiction overlap, evidence
reports, geocoded hotspot heatmap -- all persisted to MongoDB AND exported
as local files. Geospatial data served via get_geospatial_data() in
geospatial_service.py for the FastAPI backend.
```

## Key files

- `src/rag/chat.py` — `chat_turn()` / `chat_turn_stream(session_id, message)`
  are the only entry points a caller needs. Already accepts an externally
  supplied id rather than generating one — `ask.py` generates a throwaway
  `cli-<uuid>` for standalone testing, but any other caller (e.g. a FastAPI
  route) can pass its own id straight through.
- `src/rag/incident.py` — the `Incident` schema (graph-ready fields:
  `caller_number`, `mule_account`, `mule_upi`, `victim_region`,
  `amount_demanded`, `amount_lost`, `scam_type`...). Fields are filled once
  and locked; each is nudged at most once per conversation, ever
  (`EXTRACTABLE_FIELDS`, `next_missing_field()`). Guards against a known
  model failure mode where two questions get conflated into one reply and
  the user's single answer gets misattributed to two different identity
  fields (`_resolve_identity_conflict`).
- `src/rag/incident_store.py` — persists to MongoDB (falls back to local
  JSONL if Mongo is unreachable), and best-effort auto-syncs every save
  into Neo4j AND triggers a geospatial rebuild (`_sync_to_neo4j`,
  `_sync_geospatial`).
- `src/graph/` — `build.py`/`analyze.py`/`report.py` (local NetworkX
  pipeline), `neo4j_load.py`/`neo4j_queries.py`/`neo4j_run.py` (Neo4j Aura
  pipeline), `ring_intelligence.py`/`jurisdiction.py`/`court_reports.py`
  (confidence-scored fraud rings, region→state jurisdiction mapping,
  evidence report generation).
- `src/graph/geospatial.py` — Nominatim geocoding with a persistent local
  cache (`data/external/geocode_cache.json`). Any Indian city works
  automatically; no hand-coded list. `build_hotspots()` aggregates incidents
  by region, `build_geojson()` produces a GeoJSON FeatureCollection.
- `src/graph/ncrb_baseline.py` / `fetch_ncrb_data.py` — loads a 34-city
  NCRB cybercrime baseline (2021–2023) from a static JSON
  (`data/external/ncrb_cybercrime_city.json`). Run `fetch_ncrb_data` once
  to pull from the public PDF if the file is missing.
- `src/graph/heatmap.py` — Folium interactive map with two toggleable
  layers: NCRB baseline (blue) and our fraud incidents (red/orange by risk).
- `src/graph/deployment.py` — patrol deployment ranking: combined risk score
  = 0.7 × normalized(NCRB crime_rate_2023) + 0.3 × normalized(our
  incident_count), top 10 zones returned.
- `src/graph/geospatial_pipeline.py` — single shared rebuild function used
  by both the CLI (`geospatial_run.py`) and the auto-sync after every chat
  save. One place that defines what "regenerate geospatial outputs" means.
- `src/graph/geospatial_store.py` — persists snapshots to MongoDB
  (`geospatial_latest` upsert + `geospatial_runs` history).
- `src/graph/geospatial_service.py` — **the backend integration point**.
  `get_geospatial_data(include_heatmap=False)` reads `geospatial_latest`
  from Mongo and returns hotspots + deployment strategy as a dict. Pass
  `include_heatmap=True` to also get the full HTML string for serving a map
  page. Suggested FastAPI routes are in the file's docstring.

## Stack

| Concern         | Choice                                    |
|------------------|-------------------------------------------|
| Chat LLM         | Sarvam `sarvam-30b` (OpenAI-compatible API) |
| Retrieval        | FAISS (`faiss-cpu`), local, in-process |
| Embeddings       | `paraphrase-multilingual-MiniLM-L12-v2` (HuggingFace, CPU) |
| Storage          | MongoDB Atlas (separate cluster from the main app's `mongo:7` container) |
| Graph DB         | Neo4j Aura (free tier, no GDS plugin — Louvain runs in NetworkX) |
| Geocoding        | Nominatim (OpenStreetMap, via `geopy`) — cached to `data/external/geocode_cache.json` |
| Heatmap          | Folium — interactive HTML, two toggleable layers |
| NCRB baseline    | Static JSON from public PDF (34 cities, 2021–2023 data) |

## Integrating into the real app

The app already has a working chat surface: `backend/server/chatbot/`
(router → service → `ChatbotEngine.stream_reply()`), backed by a generic
Groq call with no RAG, no fraud knowledge, no field extraction — it's a
placeholder. The goal is to replace what's *inside* `ChatbotEngine`, not
add a new endpoint; the app already calls the right shape of endpoint
(`POST /chatbot/chats/{id}/messages`, SSE token stream).

Three concrete mismatches to resolve before that swap:

1. **LLM client** — `backend/server/chatbot/engine.py` uses Groq via
   LangChain; this module calls Sarvam directly via an OpenAI-compatible
   client. Either wrap this module's logic behind the same
   `stream_reply(history, message) -> AsyncIterator[str]` shape, or accept
   running two different LLM providers side by side.
2. **Mongo** — the main app uses one shared `mongo:7` container
   (`backend/shared/db.py`, async `AsyncMongoClient`, settings via
   `backend/shared/config.py`). This module currently points at a separate
   MongoDB Atlas cluster via sync `pymongo` (`src/rag/incident_store.py`).
   These need to converge onto one Mongo instance.
3. **Identity** — the main app's chats are scoped to an authenticated
   `user_id` (JWT, tied to `phone_no` in the `users` collection, which
   already collects `state`/`city`/`pin` at signup). This module's
   `Incident.session_id` is just whatever string the caller passes in —
   already flexible enough to accept the app's `chat_id`/`user_id` instead
   of generating its own, with no code change needed on this side. The
   open question is which id(s) the integration should pass through.

Geospatial is built and working — `get_geospatial_data()` in
`geospatial_service.py` is the backend integration point. The map currently
uses `victim_region` (free-text city name, Nominatim-geocoded). Precision
upgrades to PIN-level mapping become possible once chat sessions are
linkable back to a real `user_id` (the app already collects `users.pin` at
signup — mismatch #3 above is the only blocker).

## Run commands

```powershell
pip install -r requirements.txt

# Knowledge base index (once, or after editing src/rag/knowledge_base/*.md)
python -m src.rag.ingest

# Chat (standalone CLI, for testing without the real app)
python -m src.rag.ask

# Check what was extracted from a session
python -m src.graph._check session cli-<id>
python -m src.graph._check account <value>

# Fraud graph, once a few incidents exist
python -m src.graph.run                       # local NetworkX
python -m src.graph.neo4j_run                 # push to Neo4j + basic Cypher analysis
python -m src.graph.neo4j_intelligence_run    # full intelligence packages + evidence reports

# Geospatial (runs automatically after every chat save -- these are for on-demand rebuild)
python -m src.graph.fetch_ncrb_data           # one-time: fetch NCRB PDF -> data/external/ncrb_cybercrime_city.json
python -m src.graph.geospatial_run            # rebuild hotspots/heatmap/deployment + write summary.txt
```

`.env` needed: `SARVAM_API_KEY`, `MONGODB_URI`, `NEO4J_URI`,
`NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`.

## Honest limitations

See the root `README.md` in this folder for the full list (confidence
scores are a documented heuristic not a legal determination, account
linkage is inferred from shared calling infrastructure not bank
transaction data, victim identity is never collected today, jurisdiction
mapping is a small static lookup table not authoritative data).
