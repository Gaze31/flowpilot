# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

FlowPilot is a small workflow automation engine (think mini n8n/Zapier): a Python/FastAPI backend that runs DAGs of steps (trigger → LLM → action) through a Redis queue, plus a Next.js visual editor in `frontend/`. `README.md` explains the design decisions in detail.

## Commands

Backend (run from `backend/`, Python 3.12):

```bash
pip install -r requirements-dev.txt
python -m pytest -q                                  # full suite; SQLite + fakes, no Postgres/Redis/API keys needed
python -m pytest tests/test_executor.py -q           # one file
python -m pytest tests/test_executor.py::test_name   # one test
ruff check . && ruff format --check .                # CI runs both; line length 130
python -m app.worker                                 # worker process
python -m app.engine.scheduler                       # cron scheduler process
alembic upgrade head                                 # migrations (the API container runs this on start)
```

Full stack: `docker compose up --build -d` from the repo root (db, redis, api, worker, scheduler). Needs `backend/.env` with `LLM_API_KEY`/`LLM_MODEL` (Gemini); `API_KEY` locks write endpoints. Postgres is on host port 5433.

Frontend (run from `frontend/`): `npm run dev`, `npm run build`, `npm run lint`. Type-check with `npx tsc --noEmit`. Env in `.env.local`: `NEXT_PUBLIC_API_URL`, `FLOWPILOT_API_KEY` (server-only), `NEXT_PUBLIC_READ_ONLY=true` for the public demo mode.

CI (`.github/workflows/ci.yml`) only covers the backend: ruff check, ruff format check, pytest.

## Architecture

**Run lifecycle.** `POST /workflows/{id}/runs` (or the scheduler when a `trigger.schedule` cron is due) validates the graph has no cycle (`CycleError` → 422), saves a `Run` as `queued`, and `LPUSH`es only the run id onto Redis. The worker (`app/worker.py`) `BLMOVE`s the id onto a `processing` list, calls `execute_run`, and acks (removes it) in a `finally`. The DB is the source of truth; the queue never carries workflow data.

**Executor** (`app/engine/executor.py`): topological sort (Kahn's, `engine/graph.py`) → for each node, render `{{node_id.output.field}}` templates against prior outputs (`engine/templating.py`; a string that is exactly one placeholder keeps the raw type) → run the node with retries and exponential backoff. Every attempt (success or failure) is a committed `StepRun` row, which is what the UI polls. Before running, it loads this run's already-succeeded `StepRun`s and skips those nodes, so a requeued run resumes without repeating side effects.

**Crash recovery.** `engine/reaper.py` scans the processing list: finished runs are just removed; runs stuck >15 min are reset to `queued` and re-enqueued.

**Scheduler** (`engine/scheduler.py`): once a minute, matches cron expressions with croniter and dedupes per workflow+minute via Redis `SET NX EX`. Current time is injected as a parameter.

**Nodes** (`engine/nodes/`): subclass `Node`, set a unique `type` string (what the graph JSON stores), implement `async run(config, context) -> dict`, decorate with `@register`. Importing `app.engine.nodes` registers all types. Retry semantics are part of each node's contract:
- `retryable = False` for side-effecting nodes (email) so they run exactly once.
- Raise `NonRetryableError` (from `app/errors.py`) for errors that won't fix themselves (HTTP 4xx, Gemini 4xx); plain exceptions are retried (5xx, timeouts).
- Output keys `tokens_used` / `cost_usd` are picked up automatically into the `StepRun`.

**Providers are injected, never called directly.** The LLM and email nodes call functions set via `set_llm_client()` / `set_email_sender()`. `engine/providers.py::plug_in_providers()` wires real ones (Gemini over httpx, a log-only email sender) at worker startup; tests plug in fakes. Keep this pattern for any new external integration so tests stay offline and free.

**Auth.** Reads are public. Write endpoints depend on `require_api_key` (`app/api/auth.py`), which checks `X-API-Key` with `secrets.compare_digest`; if `API_KEY` is unset, writes are open (local dev/tests).

**Settings** come from env / `backend/.env` via `app/core/config.py` (`get_settings()` is `lru_cache`d).

### Tests

`tests/conftest.py` sets env vars *before* importing the app (temp SQLite DB, null pool, backoff/attempts), swaps in `fakeredis` via `queue.set_redis()`, recreates tables per test, and registers test-only node types (`test.echo`, `test.flaky`, etc.). Injectable things to use instead of real waits/clocks/services: the `fake_sleep`/`sleeps` fixtures (passed as `execute_run(..., sleep=...)`), explicit `now` parameters, `httpx.MockTransport`, and fake LLM/email providers. `chain_graph(...)` builds linear graphs. The `todo(week, ...)` marker is a strict xfail for unimplemented code; remove it once the test passes. API routes turn `NotImplementedError` into HTTP 501.

### Frontend

Next.js (App Router) + React Flow (`@xyflow/react`). Read `frontend/AGENTS.md`: this Next.js version has breaking changes, so check `node_modules/next/dist/docs/` before writing Next-specific code.

- The browser talks only to its own `app/api/*` route handlers, which proxy to the backend. Only the write routes add `X-API-Key` from the server-only `FLOWPILOT_API_KEY`; never expose it to the client. Without the key, the write routes refuse requests (that is how the read-only demo is enforced, not by hiding buttons).
- `lib/steps.ts` mirrors each backend node's config fields; `required` means the backend reads it with `config["key"]`. Update it when a node's config changes in `backend/app/engine/nodes/`.
- Run status colors live in a display-only copy of the nodes so Save never persists run results. Polling uses chained `setTimeout`, not `setInterval`. New node ids are max existing number + 1, not count + 1.

## Rules
- Never read, print or edit any .env or .env.local file, and never put keys or secrets in code.
- Never touch the AWS server or run commands with ssh.
- Never save test steps to the live demo workflow on the server.
- Use backend's own venv for Python commands.
- Before saying a task is done, run `python -m pytest -q` (in backend/) and `npx tsc --noEmit` (in frontend/) if you changed that side.
- Explain every change in simple words, file by file.