# Backend — Real-Time Scam Call Detection

Context file for Claude Code. Place at `backend/CLAUDE.md`.

## What this is

A real-time agent that joins a phone conference call, listens, and warns a user
when the conversation shows scam patterns (e.g. OTP/KYC/urgency social engineering),
tuned for Hindi/English/Hinglish. The user explicitly adds the agent to a call —
there is no silent or covert listening.

## Core principle (do not violate)

The agent only ever listens to a call it has been **added to as a participant**
(merge or dial-in conference). It is never a covert tap. Any design that captures
call audio without the participants' awareness is out of scope and not to be built.
For production, assume a recorded-line disclosure is required.

## Architecture (two processes + LiveKit)

```
Two phones dial Twilio number
      │
      ▼
Twilio TwiML <Conference>  ──SIP──►  LiveKit Cloud (media server + room)
                                          │ dispatches job (room + token)
                                          ▼
                              Agent Worker  (process 1 — worker/agent.py)
                                  • connects OUT to LiveKit, registers, idles
                                  • per call → spawns isolated subprocess (entrypoint)
                                  • entrypoint joins room, subscribes to caller audio (PCM)
                                  • PCM → Sarvam streaming STT → rolling transcript buffer
                                  • every 3–5s → send window → Groq LLM → {scam, confidence, reason}
                                  • if over threshold → notify FastAPI
                                          │
                                          ▼
                              FastAPI  (process 2 — server/app.py)
                                  • mints LiveKit access tokens (for browser test joins)
                                  • receives alerts from worker
                                  • pushes alert → Expo Push API → FCM → user's phone
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
| Storage        | MongoDB (Docker container)       | Persists call records, transcripts, detection results/alerts, device push tokens. Driver: `pymongo` async (`AsyncMongoClient`). Written by worker, read/served by FastAPI. |
| Deploy         | Docker + docker-compose          | worker container + FastAPI container + MongoDB container. LiveKit is Cloud-hosted (no LiveKit container). FastAPI exposed via ngrok for Twilio webhook + browser token fetch. |

## Python dependencies (single uv project — add at backend root)

```bash
uv add livekit-agents          # worker: cli.run_app + entrypoint, rtc audio frames
uv add livekit-api             # server: mint access tokens
uv add "fastapi[standard]"     # server: FastAPI + bundled uvicorn
uv add websockets              # shared/sarvam_stt.py: Sarvam streaming STT WS client
uv add httpx                   # server: Expo push call (+ outbound HTTP)
uv add python-dotenv           # load backend/.env in both processes
uv add pymongo                 # storage: AsyncMongoClient (worker writes, server reads)
# groq — already present
```

- `pydantic` ships with FastAPI — reuse it in `detector.py` to validate the LLM JSON; don't add separately.
- `pymongo` (not `motor`) — async support is now built into PyMongo via `AsyncMongoClient`; Motor reached end-of-life May 2026. No ODM (Beanie/MongoEngine) — pymongo + pydantic models is enough.
- `numpy` — optional; `rtc.AudioResampler` already does the 48k→16k PCM resample Sarvam needs. Add only if manipulating raw samples.
- `twilio` — optional; TwiML is served as static `conference.xml`. Only needed for dynamic TwiML / programmatic number management.

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
- **After alerting:** stop or slow re-checks for that call (already warned).

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
pLIVEKIT_URL=wss://<your-project>.livekit.cloud   # from LiveKit Cloud dashboard
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
SARVAM_API_KEY=                      # **Sarvam** streaming STT (Saaras) — from Sarvam dashboard
GROQ_API_KEY=
MONGODB_URI=mongodb://mongo:27017   # docker-compose service name; localhost:27017 for local dev
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

# FastAPI server (token endpoint + alert push)
uv run uvicorn server.app:app --reload --port 8000

# Expose FastAPI for Twilio webhook + browser token fetch (free tier OK; HTTP only)
ngrok http 8000   # update the Twilio webhook URL after each restart (URL rotates)

# Everything together (worker + server + mongo)
docker compose up
```

> **Serving:** ngrok only carries FastAPI's HTTP (token endpoint + Twilio webhook).
> WebRTC media and SIP go **directly to LiveKit Cloud**, never through ngrok — so the
> free tier is fine (no UDP tunneling needed).

This is a **single `uv` project** rooted at `backend/`: one `pyproject.toml`,
one `uv.lock`, one shared `.venv`. Both `server/` and `worker/` are part of the same
project and share dependencies, so add packages once at the backend root
(`uv add <pkg>`). Each of `server/` and `worker/` has its **own Dockerfile** so they
build as separate container images from the same source tree.

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
│   └── sarvam_stt.py         # Sarvam streaming STT WebSocket client
├── worker/                   # LiveKit agent worker (own container)
│   ├── Dockerfile
│   └── agent.py              # worker + entrypoint (audio → STT → detector → alert)
└── server/                   # FastAPI app (own container)
    ├── Dockerfile
    ├── app.py                # FastAPI: token endpoint, alert intake, Expo push
    └── twiml/conference.xml  # TwiML for the dial-in conference
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

1. `shared/detector.py` + `shared/sarvam_stt.py`, tested against a **saved audio clip**
   (zero live credits). Prove: audio → transcript → `{scam, confidence, reason}`.
2. `worker/agent.py` entrypoint wiring those into a LiveKit room; test via
   **browser/WebRTC** (no phone number needed).
3. `server/app.py` token endpoint + alert push.
4. Twilio conference → SIP → LiveKit; test with two real phones.
5. Dockerize each side (`worker/Dockerfile`, `server/Dockerfile`) and wire
   `docker-compose.yml`.

## Hackathon notes

- All services run on free tiers/credits; real spend ≈ ₹0. Only production telephony
  minutes cost money (not needed for a demo).
- Demo with a **dial-in conference** (each caller is a separate participant → you get
  per-speaker audio + each number) rather than a phone-side merge (mixed audio, no
  numbers). The conference version enables "caller +91-XXX shows scam patterns".
- Record the demo once working rather than running it live.