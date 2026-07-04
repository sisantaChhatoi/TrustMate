@AGENTS.md

# App — Scam Call Detection (React Native + Expo)

Context file for Claude Code. Place at `app/CLAUDE.md`.

## What this is

The mobile app a protected user runs. It receives real-time **scam warnings** as
push notifications while the detection agent listens to a call the user has added
it to. The app is notification-first — the alert _is_ the product.

## ⚠️ Current state vs. the backend (added 2026-06)

The app today is **auth + push-token scaffold + a (static) protection screen**.
The backend has grown well past the push-alert flow — it now also serves a **RAG
fraud-chat** and a **fraud-intelligence API** — but **those are not wired into the
app yet**. They're the obvious next screens.

### Real backend contract (this supersedes the placeholder list at the bottom)

Base URL is `API_URL` in `constants/config.ts`; the typed client is `lib/api.ts`.

- **Auth (JWT bearer):** `POST /auth/signup`, `POST /auth/login`, `GET /auth/me`,
  `POST /auth/push-token`.
- **Push test:** `POST /test/notify` — logs the JWT user's real phone, sends the
  push to the configured test number. Wired to the Test-Notify button on home.
- **Chat — NOT consumed yet:** `POST /chatbot/chats`, `GET /chatbot/chats`,
  `GET /chatbot/chats/{id}`, `POST /chatbot/chats/{id}/messages` → an **SSE
  stream** of the assistant reply. A chat screen would create a chat, then stream
  messages (use an SSE/`fetch`-stream client, not plain JSON).
- **Intelligence — NOT consumed yet:** `GET /intelligence/rings`, `/hotspots`,
  `/high-risk-accounts` → precomputed JSON for a fraud-map / dashboard screen.

### State / gotchas

- `lib/notifications.ts` registers the Expo push token (`POST /auth/push-token`).
  **Expo Go (SDK 53+) removed Android remote push** → a real token needs a **dev
  build / EAS APK**, not Expo Go. "No push token registered" downstream is this.
- `app/(tabs)/protection.tsx` currently renders **hardcoded mock stats**
  ("12 calls screened" …) — placeholder, not real data.
- Tabs are `index` (home), `alerts` (live scam alert screen), and `protection`.
  **No chat or intelligence screen exists yet.**
- Push notifications: **fully wired**. Firebase/FCM V1 credentials set up, EAS APK
  built and tested. `POST /alerts` on the backend is the production intake (worker
  → backend → FCM → phone). Tap a notification → app opens the Alerts tab.

## Stack

| Concern       | Choice                            | Notes                                                                  |
| ------------- | --------------------------------- | ---------------------------------------------------------------------- |
| Framework     | React Native + **Expo** (managed) | Web-dev friendly, fast iteration, modern UI.                           |
| Dev loop      | Expo Go (`npx expo start`)        | Scan QR, live reload on a real phone. No native build during dev.      |
| Demo build    | EAS Build → **APK**               | `eas build -p android --profile preview` → installable APK. Free tier. |
| Notifications | Expo Push Notifications           | One token for Android/iOS; Expo handles FCM/APNs underneath. Free.     |
| Live in-app   | WebSocket to FastAPI (optional)   | For foreground alerts while app is open.                               |

## Notification flow (how alerts reach the phone)

The server does **not** reach the phone directly. It goes through Expo → FCM.

```
App requests Expo push token  ──►  sends token to FastAPI backend (stored per user)
                                          │
                          (scam detected) │
                                          ▼
              Backend POSTs to Expo Push API ──► FCM ──► phone shows ⚠️ banner
```

- On launch: request notification permission, get the **Expo push token**, POST it
  to the backend so it knows where to send alerts for this user.
- Pushes arrive even when the app is backgrounded or closed (that's the point).
- For **foreground** live updates (app open during the call), also subscribe to the
  FastAPI alert **WebSocket** so the warning updates in-app instantly.

## Screens (minimal surface)

1. **Pair / Setup** — identify the user to the backend (simple ID/login for the demo),
   register the Expo push token.
2. **Monitoring state** — "Protection active" idle screen; shows when the agent is
   listening to a call.
3. **Alert** — the ⚠️ scam warning: shows `reason` and `red_flags` from the detector,
   confidence, and (if available) the flagged caller's number. This is the money screen
   for the demo — make it bold and instantly readable.

## Alert payload shape (from backend)

```json
{
  "scam": true,
  "confidence": 0.0,
  "reason": "string — why it was flagged",
  "red_flags": ["OTP request", "urgency", "account-block threat"],
  "caller": "+91XXXXXXXXXX"
}
```

Render `reason` + `red_flags` prominently; don't just show "SCAM". The explanation
is what makes it convincing.

## UI direction

Modern, high-contrast, glanceable. The alert must read in under a second — large
warning state, clear color shift (calm → alert), the reason in plain language.
Keep the idle/monitoring screen calm so the alert state contrasts sharply.

## Run / build commands

```bash
# Create (if starting fresh)
npx create-expo-app app

# Dev (live reload via Expo Go)
npx expo start

# One-time EAS setup
npm install -g eas-cli && eas login && eas build:configure

# Demo APK (standalone, installable on your phone)
eas build --platform android --profile preview
# → download link when done; enable "install from unknown sources" to sideload
```

## Notes / gotchas

- Use **Expo Go for dev** (instant reload), **EAS APK only for the final demo build**
  (don't wait per-change for cloud builds).
- Push notifications and FCM are **free**; iOS APNs would need the $99/yr Apple account,
  so the hackathon targets **Android** (APK) and skips Apple entirely.
- The first EAS build takes 10–20 min and auto-generates a keystore (accept it) —
  build the demo APK the night before recording, not last-minute.
- Backend push calls are outbound HTTPS, so a **local backend can send real pushes**
  to your phone fine (no public server needed).

## Backend contract (what the app depends on)

- `POST /register-token` — app sends its Expo push token + user id.
- `GET /token` (or similar) — mint a LiveKit access token, only if the app ever joins
  a room directly (e.g. browser-style test). Not required for the push-only flow.
- Alert WebSocket endpoint — optional, for live in-app foreground alerts.
- Backend sends pushes via Expo Push API using the stored token.
