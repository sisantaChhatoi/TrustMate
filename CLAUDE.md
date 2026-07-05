# cybersec-agent — Engineering Conventions (repo-wide)

Shared practices for **all contributors and their AI agents** (Claude Code, etc.).
Area-specific details live in `backend/CLAUDE.md` and `app/CLAUDE.md`; this file
is the baseline that applies everywhere. Read it before making changes.

## First thing in a fresh clone (per contributor, per clone)

Git hooks are **not** tracked by git, so installing them in one clone does nothing
for another. Every contributor runs this **once per clone**:

```bash
cd backend && uv sync && pre-commit install   # writes .git/hooks/pre-commit
```

- `uv sync` only makes the `pre-commit` binary available; `pre-commit install` is
  what actually activates the hook. **Both** are required — one without the other
  does nothing.
- The hook runs `ruff` (format + check), `ty` (backend type check), and
  prettier + eslint (app). Keep it green; don't `--no-verify` past failures.
- Hooks are best-effort/local. CI is the real backstop — don't rely on a
  teammate having installed them.

## When in doubt, ASK — don't assume

- If a requirement, schema, data flow, or intent is unclear, **ask before
  writing code**. A quick clarifying question beats a large wrong diff.
- Don't invent endpoints, fields, config, or "helpful" extras that weren't
  requested. Confirm scope first, then build exactly that.
- Don't guess at how an existing system works — read it, or ask.

## Code quality

- **SOLID + clean layering.** The backend is routers → services → repositories
  with dependencies injected (`server/deps.py`). Keep responsibilities
  separated: no DB access in routers, no business logic in repositories,
  single-purpose functions.
- **Type-annotate** signatures; the `ty` hook must pass.
- Match the style, naming, and structure of the surrounding code. Prefer clear
  names over cleverness.

## Comments — keep them minimal

- **No verbose, open-source-style docstrings or narration.**
- Comment only the non-obvious **why**, never the **what** — let names carry
  intent. A one-line module docstring is fine; multi-paragraph essays are not.
- **Default to zero comments.** Look at the neighbouring files: `user_repo.py`,
  `notification_service.py`, `call_monitor.py` carry almost none. Match that.
- **No method/function docstrings that just restate the signature or params.**
  `async def start(...)` needs no `"""Insert a call..."""`. If a *why* is worth
  saving, make it a single terse `# ...` line, not a multi-line docstring.

## Git / PRs

- `main` is **protected** — land changes through a **PR** (admins can bypass for
  trivial docs, but prefer PRs). Branch off `main`; don't commit straight to it.
- Stage intentionally — don't sweep unrelated changes into a commit.
- Commit messages: imperative mood, explain the *why*. Preserve authorship
  (e.g. cherry-pick keeps the original author); co-author trailers welcome.

## Keep the CLAUDE.md files honest

- When you change something core, ship a genuinely new feature, or complete
  something these docs mark "future / not wired yet", **update the relevant
  CLAUDE.md in the same change** so the docs never contradict the code. Fix
  now-stale lines instead of leaving them.
- Add new prose only if a future session would genuinely trip without it, and
  keep it **minimal**. Don't pad these files with full project descriptions,
  tutorials, or filler — high-signal only.
