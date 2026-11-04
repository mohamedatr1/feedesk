# M1 Completion — Subagent Brief

**Repo root:** `F:\FeeDesk`  
**Date:** 3 November 2026  
**Goal:** Finish the remaining M1 foundation work without changing M0/G0 scope or starting M2+.

## Read first

1. `README.md`
2. `docs/progress.md`
3. `docs/m1/status.md`
4. M1 section of `FeeDesk-Delivery-Plan.md` (section 8.2)
5. Relevant ADRs in `docs/adr/`

## Current state

- M1 foundation is working locally.
- Backend: FastAPI, PostgreSQL 16, 19-table schema, Alembic, auth/session/CSRF/RBAC, users, school settings, audit, private storage, health.
- Frontend: Next.js 16 RTL, login, forced password change, shell, dashboard empty state, settings, users, audit, placeholders.
- 13 backend tests pass; Ruff, TypeScript, production build pass.
- G0 is blocked by Rasel trial/sender/sample issues; do not attempt live SMS or claim G0 is passed.

## Environment

- Python: `F:\FeeDesk\.venv\Scripts\python.exe`
- API working dir: `F:\FeeDesk\apps\api`
- Web working dir: `F:\FeeDesk\apps\web`
- Local PostgreSQL: `127.0.0.1:55432`, DB `feedesk`
- Test DB: `feedesk_test` (created by `tests/conftest.py`)
- `.env.local` contains secrets. Do not read it aloud, print it, commit it, or copy its values into source/docs.
- Do not touch `.local/`, `PRD.md`, `FeeDesk-Delivery-Plan.md`, `FeeDesk-Task-Register.csv`, `docs/progress.md`, or `docs/m1/status.md` unless your lane explicitly owns them.
- Do not send SMS, create real campaigns, or use real guardian data.

## Checks

```powershell
# backend
Set-Location F:\FeeDesk\apps\api
& F:\FeeDesk\.venv\Scripts\ruff.exe check app tests
& F:\FeeDesk\.venv\Scripts\python.exe -m pytest -q

# frontend
Set-Location F:\FeeDesk\apps\web
npm run typecheck
$env:NODE_OPTIONS="--max-old-space-size=2048"
npm run build
```

Do not start long-running dev servers. The build is memory-sensitive; use the NODE_OPTIONS above.

## Rules

- Preserve Arabic RTL and the existing calm green/cream visual language.
- Keep changes bounded to your lane.
- Do not weaken authentication, CSRF, RBAC, audit append-only behavior, or money/currency rules.
- Do not add AI to financial decisions.
- Write tests for behavior you change.
- Report: files changed, tests run/results, remaining risks, and anything the orchestrator must verify.
