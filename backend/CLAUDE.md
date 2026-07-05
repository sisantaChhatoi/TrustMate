# Backend — Real-Time Scam Call Detection

Context file for Claude Code. Place at `backend/CLAUDE.md`.

> Repo-wide conventions — code style, minimal comments, pre-commit setup, SOLID,
> "ask, don't assume" — live in the **root `CLAUDE.md`**. Read that first; this
> file is backend-specific.

## What this is

A real-time agent that joins a phone conference call, listens, and warns a user
when the conversation shows scam patterns (e.g. OTP/KYC/urgency social engineering),
tuned for Hindi/English/Hinglish. The user explicitly adds the agent to a call —
there is no silent or covert listening.

## ⚠️ Scope has grown — read this (added 2026-06)

This service is now **two products in one FastAPI app**:

1. **Real-time call-listening agent** — the LiveKit/Twilio pipeline documented
   in the rest of this file (`worker/`). Still valid.
2. **Text RAG fraud-chat + a fraud-intelligence graph layer** (`server/`),
   migrated in from the former `rag-graph/` prototype. **`rag-graph/` is now
   deleted**; its design notes live in `backend/docs/fraud-intelligence-overview.md`.

### Layout of the `server/` side (layered: routers → services → repositories)

```
server/
  routers/       auth, chatbot, intelligence, alerts, notifications, test
  services/      auth_service, chatbot_service, notification_service
  repositories/  user_repo, chat_repo, incident_repo, intelligence_repo,
                 notification_repo
  chatbot/       engine (LangChain agent loop), llm (provider factory),
                 tools (save/update/lookup + KB search), retrieval (FAISS)
  graph/         build, analyze, geospatial, deployment, ncrb_baseline,
                 neo4j_*, pipeline, __main__   ← the intelligence batch job
  core/          security (JWT)
  models/        user, chat, incident, notification
  deps.py        DI wiring (db, repos, services, current-user)
```
Mongo via `shared/db.py` (`AsyncMongoClient`); all settings in `shared/config.py`.

### RAG fraud-chat
- LangChain **tool-calling agent over Sarvam** (`make_chat_llm()` factory; Groq
  is the alternate via `chat_provider`). Manual stream loop in `engine.py`
  (no LangGraph); replies stream over **SSE**.
- Endpoints: `POST /chatbot/chats`, `GET /chatbot/chats`,
  `GET /chatbot/chats/{id}`, `POST /chatbot/chats/{id}/messages` (SSE).
- Tools live in `chatbot/tools.py` — **field semantics are in the tool
  docstrings, not the prompt**: `search_fraud_knowledge` (FAISS over the KB),
  `save_incident` (fill-once-then-lock merge), `update_incident` (corrections
  only), `lookup_fraud_network` (point lookup of a number/account/UPI across
  *other* incidents). Built per-request with session/user bound.
- Prompt (`engine.py`): capture-first, ground via the search tool, prefer
  Hindi/Hinglish, settle in 2–3 clarifications, never ask for OTP/PIN.

### Fraud-intelligence graph (the strong part)
- **Scheduled rebuild:** `server/graph/scheduler.py` runs `pipeline.run()` on
  an `AsyncIOScheduler` interval (default 6h, configurable via
  `GRAPH_REBUILD_INTERVAL_HOURS`). Starts automatically with the FastAPI app.
  For a one-off/first-time seed: `python -m server.graph`. The job reads
  incidents from Mongo → NetworkX co-occurrence graph → Louvain fraud rings →
  per-entity risk scoring → geocoded geospatial hotspots + NCRB-weighted
  deployment ranking → writes snapshot docs to the `intelligence` collection;
  best-effort Neo4j load.
- **Read API (app dashboard):** `GET /intelligence/rings`, `/hotspots`
  (+ deployment strategy), `/high-risk-accounts`. Read-only, served straight
  from the precomputed snapshots.
- **Tool-vs-API split:** point lookups are chat *tools*; aggregates are the
  *API*; graph build is the *batch job*.
- **Neo4j** runs locally via Docker (`docker-compose.yml`); native vector index
  + cosine is confirmed working (for a future GraphRAG / similarity pass).

### Gotchas (future sessions — don't relearn these the hard way)
- **`sarvam-m` is DEPRECATED** → use `sarvam-30b` / `sarvam-105b`
  (`sarvam_chat_model`). It 400s otherwise.
- **`/intelligence` only ever reads precomputed snapshots.** Never run the graph
  build in the request path. In prod the scheduler handles rebuilds automatically.
  If the endpoints return empty on first boot, seed once with `python -m server.graph`
  (the scheduler only fires after the first interval has elapsed).
- **Neo4j is optional for the batch.** The load is best-effort; the job logs
  `neo4j_error` and finishes fine if the container is down.
- **Geocoding** uses Nominatim with a committed cache at
  `server/graph/data/geocode_cache.json` (1 req/s; caches misses too). A city
  not in the cache hits the network once.
- **The async Mongo client is `@lru_cache`d** → it binds to the first event
  loop. `TestClient` spins a fresh loop per request, so calling several
  endpoints in one `TestClient` process can raise a Mongo loop error — a **test
  artifact, not a server bug** (uvicorn uses one persistent loop). Smoke-test one
  endpoint per process, or use `httpx.AsyncClient` + `ASGITransport`.
- **Type checking:** a **`ty`** (Astral) pre-commit hook runs on
  `backend/{server,worker,shared}`; keep it green. The teammate's scratch
  `test/*.ipynb` is excluded. Pydantic gotcha already handled: pass `SecretStr`
  for `ChatOpenAI(api_key=...)`.
- **Incident identity guard:** `caller_number` / `mule_account` / `mule_upi`
  must never share a value; a real account number (`\d{6,}`) overwrites.
- **Push notifications:** fully wired end-to-end. Token register → store →
  `POST /test/notify` (test loop) + `POST /alerts` (production path: worker calls
  this with `{user_id, confidence, reason, red_flags}`; backend looks
  up the push token and sends via Expo Push API → FCM). FCM V1 credentials uploaded
  to EAS. APK built via `eas build -p android --profile preview`; CI/CD pipeline
  auto-builds on release tags (`.github/workflows/build-apk.yml`).
- **Call records + alert path (worker → `calls` collection + `POST /alerts`):**
  On connect the worker identifies the **caller as the registered user** (the user
  dials our agent), resolves `user_id` via `shared/repositories/user_directory.py`
  (`phone_no` lookup), and upserts a `CallRecord` (`shared/models/call.py`) keyed on
  `room_name` — idempotent, so re-runs on participant-join and re-dispatch don't
  duplicate. On disconnect (`ctx.add_shutdown_callback`) it stamps `ended_at`.
  Persistence is **best-effort**: a DB outage logs and the call is still monitored.
  Alerts are **throttled per call** via `CallRepository.claim_notification` (atomic
  `last_notified_at` gate, `ALERT_THROTTLE_SECONDS`, default 60s) so a sustained
  scam re-alerts at most once/minute. `ALERT_INTAKE_URL` is the worker→FastAPI
  target (`http://server:8000/alerts` under compose; localhost for local dev).
- **Notification history:** on a successful push, `POST /alerts` persists the alert
  (the payload fields + a server-stamped `sent_at`) to the `notifications` collection.
  `GET /notifications` returns them newest-first, **JWT-scoped to the current user**
  (no `user_id` path param — a user only ever sees their own). This is what the app
  reads to render an alerts history.

## Core principles (do not violate)

1. **No covert listening.** The call agent only ever listens to a call it has
   been **added to as a participant** (merge or dial-in conference) — never a
   covert tap. No design that captures call audio without the participants'
   awareness. For production, assume a recorded-line disclosure is required.
2. **Never solicit secrets, never act for the user.** The chat assistant must
   never ask for an OTP, PIN, password, or card number, and never performs a
   transaction or any action on the user's behalf — it only advises and points
   to reporting (1930 / cybercrime.gov.in).
3. **Intelligence is advisory, not a verdict.** Fraud rings, risk levels, and
   hotspots are **heuristics for prioritization, not verified determinations** of
   guilt. Never present them as accusations or proof — label them as signals.
   The deployment methodology already carries this disclaimer; keep it.
4. **Match the scammer's identifiers; protect the victim's identity.** The mule
   account / UPI / caller number are the *attacker's* fingerprints — matching and
   showing them across incidents is the whole product (`lookup_fraud_network`,
   `/intelligence`), and that is intended. What must never leak is the **person
   who reported an incident**: never expose `user_id` or tie a scammer identifier
   back to who reported it. Cross-incident results stay aggregate (counts, scam
   types, linked *scammer* entities — never reporters), and `victim_region` is
   surfaced at city level only. Don't add endpoints that expose per-user incident
   detail or `user_id` without auth scoping.
5. **Graph build stays out of the request path.** `/intelligence` serves only
   precomputed snapshots; the NetworkX/Neo4j build runs only as the offline
   batch job (`python -m server.graph`).

## Architecture (call agent + chat API + intelligence batch)

Three surfaces share **one MongoDB** (collections: `users`, `chats`,
`incidents`, `intelligence`, `calls`, `notifications`). FastAPI (`server/app.py`) fronts the chat + read
APIs and the alert intake; the worker and the graph job are separate runtimes.

```
A. REAL-TIME CALL AGENT  (worker/)
   Two phones → Twilio TwiML <Conference> ─SIP→ LiveKit Cloud (room + job dispatch)
     → Agent Worker (connects OUT; one isolated subprocess per call)
         caller PCM → Sarvam streaming STT → rolling transcript window
         → every 3–5s → Groq LLM → {scam, confidence, reason, red_flags}
         → over threshold → POST alert → FastAPI → Expo Push API → FCM → phone

B. RAG FRAUD-CHAT  (server/chatbot/, request path)
   App → FastAPI POST /chatbot/chats/{id}/messages (SSE)
     → LangChain tool-calling agent over Sarvam
         tools: search_fraud_knowledge (FAISS) · save_incident / update_incident
                · lookup_fraud_network (point query)
     → streams reply to app; persists extracted incidents ───────────► Mongo

C. FRAUD-INTELLIGENCE  (server/graph/, offline batch + read API)
   Batch `python -m server.graph`: reads incidents ◄──────────────── Mongo
     → NetworkX co-occurrence graph → Louvain rings + per-entity risk
     → geocoded hotspots + NCRB deployment ranking
     → writes `intelligence` snapshots ──────► Mongo  (+ best-effort Neo4j load)
   App → FastAPI GET /intelligence/{rings,hotspots,high-risk-accounts}
     → reads precomputed snapshots ◄──────────────────────────────── Mongo
```

### Key facts about the worker
- The worker **connects out** to LiveKit over a persistent WebSocket and waits for
  jobs. It is **NOT an HTTP server** — it has no inbound endpoints. Nothing calls into it.
- `cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))` runs the
  receive-job → spawn-subprocess → run `entrypoint` loop. You only write `entrypoint`.
- **One worker handles many calls.** Each call = one job = one isolated subprocess
  (actor-style isolation; one call crashing can't affect others).
- Scale horizontally by running more worker instances; LiveKit load-balances jobs.
  No code change to add capacity.

## Stack

| Concern        | Choice                          | Notes |
|----------------|----------------------------------|-------|
| Telephony      | Twilio (trial number for demo)   | TwiML `<Conference>`, SIP trunk into LiveKit Cloud. Trunk + dispatch rule configured in LiveKit Cloud dashboard (Telephony → Configuration) or via `lk sip` CLI. US number for hackathon; Indian DID (Plivo/Exotel, KYC) is the production path. |
| Media / agent  | LiveKit **Cloud** (free tier)    | Agents framework (Python). Cloud is the managed media server + room + SIP endpoint — no LiveKit container to run or ports to open. Worker connects out to the Cloud `wss://` URL. |
| STT            | Sarvam **streaming** STT         | WebSocket, Saaras v3. Hinglish/code-mixing, diarization, <150ms first token. |
| LLM (detector) | Groq — Llama 3.3 70B             | OpenAI-compatible API, fast, free tier. (Sarvam's LLM is a free Hinglish-native alternative.) |
| Push           | Expo Push API → FCM              | Outbound HTTPS from server; works from localhost. |
| Storage        | MongoDB (Docker container)       | Persists call records (`calls`), alert history (`notifications`), device push tokens (`users`), plus chat + incident data. Driver: `pymongo` async (`AsyncMongoClient`). Worker writes calls; server writes/reads the rest. |
| Deploy         | Docker + docker-compose          | worker container + FastAPI container + MongoDB container. LiveKit is Cloud-hosted (no LiveKit container). FastAPI exposed via ngrok so the phone app can reach the API. |

## Python dependencies (single uv project — add at backend root)

```bash
uv add livekit-agents          # worker: cli.run_app + entrypoint, rtc audio frames
uv add livekit-api             # worker group: LiveKit server SDK (not currently wired)
uv add "fastapi[standard]"     # server: FastAPI + bundled uvicorn
uv add websockets              # shared/stt/sarvam.py: Sarvam streaming STT WS client
uv add httpx                   # server: Expo push call; worker: POST /alerts
uv add python-dotenv           # load backend/.env in both processes
uv add pymongo                 # storage: AsyncMongoClient (worker writes, server reads)
# groq — already present
```

- `pydantic` ships with FastAPI — reuse it in `detector.py` to validate the LLM JSON; don't add separately.
- `pymongo` (not `motor`) — async support is now built into PyMongo via `AsyncMongoClient`; Motor reached end-of-life May 2026. No ODM (Beanie/MongoEngine) — pymongo + pydantic models is enough.
- `numpy` — optional; `rtc.AudioResampler` already does the 48k→16k PCM resample Sarvam needs. Add only if manipulating raw samples.
- `twilio` — optional; the TwiML lives on the Twilio side (`sip/twiml-bin.xml` is the committed template that dials into the LiveKit SIP trunk). Only needed for dynamic TwiML / programmatic number management.

## Detection logic (the business logic)

Lives in a shared module `detector.py`, imported by the worker (and reusable by FastAPI).

- **Input:** a rolling window of the last ~30–45s of transcript (NOT the whole call,
  NOT a tiny 2–3 message chunk). Pass prior context each call so the model judges
  intent as it builds across the conversation.
- **Trigger:** run every 3–5 seconds (frequent checks feel real-time). The trigger
  interval and the context-window size are independent knobs — tune frequency up,
  keep the window wide.
- **Prompt:** ask for strict JSON: `{ "scam": bool, "confidence": 0..1, "reason": str, "red_flags": [str] }`.
  Red flags to watch: OTP/PIN requests, KYC-update pressure, account-blocking threats,
  urgency, UPI/payment pressure, impersonation of bank/police.
- **Hysteresis:** do NOT alert on a single positive. Require confidence over a
  threshold AND/OR two consecutive positive windows, to avoid false alarms mid-call.
- **After alerting:** `AlertPolicy` re-arms (streak resets) rather than latching
  once-per-call; the DB time-throttle (`claim_notification`, default 60s) is what
  actually caps how often an alert reaches the user for a sustained scam.

## Latency notes

- The latency floor is the **STT**, not the LLM. Use Sarvam's **streaming** WebSocket
  endpoint (not REST/batch) or it will feel laggy.
- Groq is fast enough that the 3–5s batch interval is never the bottleneck.
- US-number → India round-trip adds a few hundred ms; invisible for a listen-and-warn
  product (the warning just lands a beat later).

## Audio format constraints

- LiveKit delivers PCM audio frames.
- Sarvam streaming WebSocket accepts **WAV or raw PCM only** (no MP3/AAC), **16kHz**.
  Feed raw PCM at 16kHz; specify `input_audio_codec` for PCM.

## Environment variables

```
LIVEKIT_URL=wss://<your-project>.livekit.cloud   # from LiveKit Cloud dashboard
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
SARVAM_API_KEY=                      # **Sarvam** streaming STT (Saaras) — from Sarvam dashboard
GROQ_API_KEY=
MONGODB_URI=mongodb://mongo:27017   # docker-compose service name; localhost:27017 for local dev
GRAPH_REBUILD_INTERVAL_HOURS=6     # how often the scheduler rebuilds the intelligence snapshots (default 6)
# Twilio creds not needed for the dial-in demo (Twilio → webhook, static TwiML, SIP via console).
# Add TWILIO_AUTH_TOKEN only for webhook signature validation or Twilio REST API calls.
# Expo push needs no server-side key when using Expo's push service.
```

## Run commands

```bash
# LiveKit is Cloud-hosted — nothing to run locally. Just set LIVEKIT_URL/KEY/SECRET.

# MongoDB (local dev; docker compose runs this for you otherwise)
docker run --rm -p 27017:27017 -v mongo-data:/data/db mongo:7

# Agent worker (long-running; spawns a subprocess per call)
uv run python -m worker.agent dev

# FastAPI server (app API: auth + chat + intelligence + alert intake)
uv run uvicorn server.app:app --reload --port 8000

# Expose FastAPI so the phone app can reach the API (free tier OK; HTTP only)
ngrok http 8000   # URL rotates on restart — update the app's API base URL

# Everything together (worker + server + mongo)
docker compose up
```

> **Serving:** ngrok only carries FastAPI's HTTP (the app's API calls).
> WebRTC media and SIP go **directly to LiveKit Cloud**, never through ngrok — so the
> free tier is fine (no UDP tunneling needed).

This is a **single `uv` project** rooted at `backend/`: one `pyproject.toml`,
one `uv.lock`, one shared `.venv`. Deps are split into groups so each image installs
only its slice: base `[project.dependencies]` (used by `shared/`), plus a `server`
group and a `worker` group. Local dev / pre-commit / `ty` get the full surface via
`default-groups`; each Dockerfile narrows with `--no-default-groups --group <name>`.
Add a package to the right group (`uv add --group server <pkg>`); base only for things
`shared/` needs. `torch` is pinned to the PyTorch **CPU** index (see `[tool.uv.sources]`)
— this is a CPU-only deployment, so we skip the multi-GB CUDA wheel. Each of `server/`
and `worker/` has its **own Dockerfile** so they build as separate container images.

> **Native-Linux contributors:** the Dockerfiles use a BuildKit uv cache mount
> (`RUN --mount=type=cache …`), so you need the **buildx** plugin — e.g. Arch:
> `sudo pacman -S docker-buildx`, Debian/Ubuntu: `docker-buildx-plugin`. Without it
> `docker compose up --build` errors with *"the --mount option requires BuildKit"*.
> **Mac/Windows Docker Desktop already bundles it** — nothing to install.

## File layout (actual — single uv project)

```
backend/                      # uv project root (pyproject.toml, uv.lock, .venv, .python-version)
├── CLAUDE.md
├── main.py                   # uv-init entry placeholder — repurpose or remove
├── pyproject.toml            # shared deps for BOTH server and worker
├── uv.lock
├── docker-compose.yml        # orchestrates worker + server + mongo (LiveKit is Cloud-hosted)
├── shared/                   # code imported by BOTH server and worker
│   ├── detector.py           # scam-detection logic (Groq call + JSON schema + hysteresis)
│   ├── db.py                 # AsyncMongoClient handle
│   ├── config.py             # all settings (pydantic-settings)
│   ├── stt/                  # Sarvam streaming STT client (base + factory + sarvam)
│   ├── models/call.py        # CallRecord (persisted per call)
│   └── repositories/         # call_repo (calls collection) + user_directory (phone→user_id)
├── worker/                   # LiveKit agent worker (own container)
│   ├── Dockerfile
│   ├── agent.py              # worker + entrypoint (audio → STT → detector → alert)
│   ├── call_monitor.py       # per-track transcribe → detect → on_alert loop
│   └── call_recorder.py      # per-call persistence + throttled POST /alerts
└── server/                   # FastAPI app (own container)
    ├── Dockerfile
    ├── app.py                # create_app: registers routers + ensure_indexes on startup
    ├── deps.py               # DI wiring (db, repos, services, current-user)
    ├── routers/              # auth, chatbot, intelligence, alerts, notifications, test
    ├── services/             # auth_service, chatbot_service, notification_service
    ├── repositories/         # user, chat, incident, notification, intelligence
    ├── models/               # user, chat, incident, notification
    ├── core/                 # security (JWT)
    ├── chatbot/              # LangChain engine + tools + FAISS retrieval
    └── graph/                # fraud-intelligence batch job
```

Notes:
- `server/` = the FastAPI process. `worker/` = the LiveKit agent process. They are
  **two separate runtimes** (and two containers), not one app — keep that boundary.
- Put anything used by both (the detector, the Sarvam client, shared models/config)
  in `shared/` so there's one source of truth. Both dirs import from `shared`.
- The root `main.py` is the default `uv init` file; either delete it or repurpose it
  (e.g. a tiny dev launcher). The real FastAPI app lives in `server/app.py`.
- Because it's one uv project, run modules with `uv run python -m worker.agent` /
  `uv run uvicorn server.app:app` so imports resolve from the backend root.

## Build order (do the smallest loop first)

1. `shared/detector.py` + `shared/stt/sarvam.py`, tested against a **saved audio clip**
   (zero live credits). Prove: audio → transcript → `{scam, confidence, reason}`.
2. `worker/agent.py` entrypoint wiring those into a LiveKit room; test via
   **browser/WebRTC** (no phone number needed).
3. `server/app.py` alert intake (`POST /alerts`) + Expo push.
4. Twilio conference → SIP → LiveKit; test with two real phones.
5. Dockerize each side (`worker/Dockerfile`, `server/Dockerfile`) and wire
   `docker-compose.yml`.