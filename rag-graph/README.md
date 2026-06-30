# Digital Arrest Shield — Fraud Intelligence Chat & Graph

A multilingual chat assistant for the "Citizen Fraud Shield": someone
describes a suspicious call/message, gets a grounded, in-language risk
verdict and safety advice — while the system quietly collects the details
(caller number, mule account/UPI, amount, region) that matter for tracing
the scam network behind it. Those incidents feed a fraud network graph that
surfaces reused accounts, fraud rings, and multi-state operations.

## Architecture

```
User chats (Hindi / Hinglish / English)
        |
        v
src/rag/   RAG chat: multilingual embeddings + FAISS retrieval over a fraud
        |  knowledge base -> Sarvam-30B generates a grounded, in-language
        |  reply -> a background extraction pass fills in structured fields
        |  one at a time (each asked at most once). At most one extraction
        |  worker runs per session -- fast typing never builds a backlog.
        v
MongoDB Atlas: digital_arrest_shield.incidents  <- source of truth
        |
        | every save triggers three best-effort background syncs:
        |   1. Neo4j -- idempotent graph update for this incident
        |   2. Geospatial -- rebuilds hotspot map + deployment ranking
        |      from all incidents so the map is always current
        v
src/graph/  fraud network graph AND geospatial intelligence:
        |     - local: in-memory NetworkX + Louvain community detection
        |     - Neo4j Aura: Cypher pattern queries
        |     - geospatial: Nominatim geocoding (cached), NCRB baseline
        |       overlay, patrol deployment ranking, Folium heatmap
        v
Fraud rings, reused/high-risk accounts, jurisdiction overlap, evidence
reports, geocoded hotspot heatmap -- persisted to MongoDB AND local files.
Geospatial data exposed via get_geospatial_data() for the FastAPI backend.
```

## Components

### Chat (`src/rag/`)
- `embedder.py` — loads `paraphrase-multilingual-MiniLM-L12-v2` once (CPU,
  multilingual incl. Hindi/Hinglish).
- `vector_store.py` — FAISS index wrapper (build/save/load/search).
- `ingest.py` — chunks `knowledge_base/*.md`, embeds, builds the FAISS
  index. Rerun after editing the knowledge base: `python -m src.rag.ingest`.
- `retriever.py` — embeds a query, searches the index, filters out
  low-relevance matches (a short reply like "SBI" shouldn't drag in
  unrelated chunks).
- `chat.py` — `chat_turn()` / `chat_turn_stream()` are the only functions a
  UI needs. Handles the grounded reply, the one-field-at-a-time data
  collection (asks each missing field exactly once, never loops on it),
  background field extraction (doesn't block the reply), and a repetition
  guard against the underlying model's tendency to repeat itself verbatim
  in long conversations.
- `incident.py` / `incident_store.py` — the `Incident` schema (graph-ready
  fields: `caller_number`, `mule_account`, `mule_upi`, `victim_region`,
  `amount_demanded`, `amount_lost`, `scam_type`, ...) and its persistence —
  MongoDB, falling back to a local `data/rag/incidents.jsonl` if Mongo is
  ever unreachable. If Neo4j credentials are configured, every save also
  auto-syncs that incident into the graph immediately (best-effort —
  failures here never break saving the chat data itself).
- `knowledge_base/*.md` — the fraud-advisory documents RAG retrieves from
  (digital arrest, courier/KYC/UPI/job/investment/lottery scams, reporting
  procedures, a cybercrime-terms glossary).
- `ask.py` — manual test CLI: `python -m src.rag.ask` (interactive, keeps
  memory), `python -m src.rag.ask "message"` (one-shot), `--stream` to see
  token-by-token streaming.

### Graph intelligence (`src/graph/`)

**Local pipeline** (no external graph DB required):
- `data.py` — loads incidents from MongoDB.
- `build.py` — builds the in-memory graph (nodes: mule account, phone
  number, victim region, scammer UPI ID; an edge between every pair of
  entities that co-occurred in the same incident).
- `analyze.py` — Louvain community detection (fraud rings) + per-entity
  risk scoring.
- `report.py` / `run.py` — writes `network_graph.graphml`,
  `fraud_rings.json`, `account_intelligence.json`, `summary_report.txt`.
  Run: `python -m src.graph.run`.
- `visualize.py` — quick static PNG of the graph, no extra software needed:
  `python -m src.graph.visualize`.

**Neo4j Aura pipeline** (a real graph database, Cypher queries):
- `neo4j_client.py` / `neo4j_load.py` / `neo4j_queries.py` — connects, pushes
  incidents as a property graph, runs the Cypher pattern queries
  (high-degree/reused accounts, regional hotspots, accounts sharing a
  phone number, accounts spanning multiple regions).
- `neo4j_run.py` — clears + rebuilds the graph fresh from MongoDB, runs the
  basic Cypher analysis. Run: `python -m src.graph.neo4j_run`.
- `ring_intelligence.py` / `jurisdiction.py` / `court_reports.py` /
  `evidence_store.py` / `neo4j_intelligence_run.py` — the full
  intelligence-package layer: confidence-scored rings (formula shown, not
  asserted), core members, region→state jurisdiction mapping, a
  chronological evidence chain per ring. **Read-only** against the graph
  Neo4j already has — doesn't re-push or clear anything. Run:
  `python -m src.graph.neo4j_intelligence_run`.

**Geospatial intelligence pipeline:**
- `geospatial.py` — Nominatim geocoding (OpenStreetMap, via `geopy`) with a
  persistent local cache at `data/external/geocode_cache.json`. Any Indian
  city a user types gets looked up automatically and cached permanently — no
  hand-coded city list. `build_hotspots()` aggregates incidents by region.
- `ncrb_baseline.py` / `fetch_ncrb_data.py` — 34-city NCRB cybercrime
  baseline (2021–2023) from a public PDF, stored as static JSON. Run
  `fetch_ncrb_data` once if the file is missing.
- `heatmap.py` — Folium interactive map, two toggleable layers: NCRB
  baseline (blue markers) and our fraud incidents (red = high risk, orange =
  normal). Output: `data/graph/geospatial_heatmap.html`.
- `deployment.py` — patrol deployment ranking. Combined risk score =
  0.7 × normalized(NCRB crime_rate_2023) + 0.3 × normalized(our
  incident_count). Top 10 zones with methodology documented in output.
- `geospatial_pipeline.py` — shared rebuild function used by both the CLI
  and the auto-sync after every chat save.
- `geospatial_store.py` — persists to MongoDB: `geospatial_latest` (single
  upsert) + `geospatial_runs` (timestamped history).
- `geospatial_service.py` — **FastAPI integration point**. Call
  `get_geospatial_data(include_heatmap=False)` to get hotspots + deployment
  strategy as a JSON-serializable dict. Pass `include_heatmap=True` to also
  get the full HTML string for serving the map page directly. Suggested
  FastAPI routes are in the file's docstring.
- `geospatial_run.py` — CLI for on-demand rebuild + human-readable
  `geospatial_summary.txt`. Run: `python -m src.graph.geospatial_run`.

## Setup

`.env` (gitignored, never hardcoded):
```
SARVAM_API_KEY=...
MONGODB_URI=mongodb+srv://...
NEO4J_URI=neo4j+s://...
NEO4J_USERNAME=...
NEO4J_PASSWORD=...
NEO4J_DATABASE=...
```

```
pip install -r requirements.txt
```

First run downloads the multilingual embedding model (~470MB). If your `C:`
drive is tight on space, point the cache elsewhere first:
```powershell
$env:HF_HOME = "D:\path\to\cache"
```

## Running it

```powershell
# 1. Build the knowledge-base index (once, or after editing knowledge_base/*.md)
python -m src.rag.ingest

# 2. Chat
python -m src.rag.ask

# 3. Check what was extracted from a session
python -m src.graph._check session cli-<id>

# 4. Once a few conversations exist, build/analyze the fraud graph
python -m src.graph.run                       # local NetworkX
python -m src.graph.visualize                 # quick PNG
python -m src.graph.neo4j_run                 # push to Neo4j + basic Cypher analysis
python -m src.graph.neo4j_intelligence_run    # full intelligence packages + evidence reports

# 5. Geospatial (auto-runs after every chat save -- these are for on-demand use)
python -m src.graph.fetch_ncrb_data           # one-time: fetch NCRB baseline
python -m src.graph.geospatial_run            # rebuild + write geospatial_summary.txt
```

## Where everything actually lives

- **MongoDB Atlas** (the real source of truth):
  - `digital_arrest_shield.incidents` — every conversation's extracted
    fields plus the full transcript.
  - `digital_arrest_shield.fraud_rings` — ring intelligence, including the
    rendered evidence report text (not just structured data).
  - `digital_arrest_shield.fraud_intelligence_runs` — one document per
    analysis run (summary stats, jurisdiction alerts), timestamped.
  - `digital_arrest_shield.geospatial_latest` — single always-current
    geospatial snapshot (hotspots, deployment strategy, heatmap HTML).
    Updated automatically after every chat save.
  - `digital_arrest_shield.geospatial_runs` — lightweight timestamped
    history of each rebuild (hotspot count + top deployment zones).
- **Neo4j Aura** — the graph itself, fully rebuilt from MongoDB on every
  `neo4j_run.py` call; nothing here is irreplaceable.
- **Local files** (`data/graph/`, `data/graph_neo4j/`, gitignored) —
  disposable exports of the exact same content above, for reading without
  a DB client. Safe to delete anytime; rerunning the pipeline regenerates
  them identically.
- **`data/external/geocode_cache.json`** — persistent Nominatim cache.
  Commit this file so teammates don't re-hit the API for cities already
  looked up. `data/external/ncrb_cybercrime_city.json` — static NCRB data,
  also commit.

## Honest limitations

- Confidence scores on fraud rings are a transparent, documented heuristic
  (see `ring_intelligence.py` — the formula travels with the score), not a
  verified legal determination.
- Account linkage ("money chains") is inferred from shared calling
  infrastructure — the same phone number used with multiple accounts — not
  literal bank transaction data, which this project never has access to.
- Every generated evidence report carries an explicit disclaimer: this is
  investigative-support output to help triage and prioritize, not a
  substitute for formal evidentiary procedure.
- Victim identity is never collected — incidents are keyed by an anonymous
  chat `session_id` by design.
- Region→state jurisdiction mapping is a small static city lookup table
  (`src/graph/jurisdiction.py`), not authoritative administrative data —
  unrecognized cities map to `"Unknown"` rather than a guess.
- Neo4j Aura's free tier has no Graph Data Science plugin, so Louvain
  community detection runs in NetworkX after pulling the graph back out of
  Neo4j, not inside Neo4j itself.

## Tech stack

- **Sarvam `sarvam-30b`** (OpenAI-compatible API) — chat generation and
  structured-field extraction.
- **`paraphrase-multilingual-MiniLM-L12-v2`** (HuggingFace, CPU) —
  multilingual retrieval embeddings, including Hindi/Hinglish.
- **FAISS** (`faiss-cpu`) — local knowledge-base vector index.
- **MongoDB Atlas** — incident storage and the durable evidence copy.
- **Neo4j Aura** + **NetworkX** (Louvain) — fraud network graph analysis.
- **Nominatim / geopy** — free OpenStreetMap geocoding, India-scoped, cached
  locally so any city works without a hand-coded list.
- **Folium** — interactive HTML heatmap with toggleable layers.
- **NCRB cybercrime baseline** — 34-city 2021–2023 data from a public PDF,
  used to weight the patrol deployment ranking.
