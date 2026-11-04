# Vercel Services Configuration

**Status:** Configuration implemented and deployed to `https://feedesk-one.vercel.app`. See `vercel-deployment.md` for the live deployment record. This does not replace the G0/G4/G5, security, backup, monitoring, or school sign-off gates.

## Architecture

- `web` (Next.js) is the only public service. The catch-all rewrite sends all public traffic to it.
- `api` (FastAPI) is **internal**. It has no public top-level rewrite.
- `web` declares a service binding to `api`; Vercel injects the internal base URL as `API_URL`.
- Browser requests to `/api/*` reach the Next.js bridge at `apps/web/app/api/[...path]/route.ts`, which forwards them to FastAPI using `API_URL`.
- Locally and in Docker, the bridge falls back to `API_INTERNAL_URL` and then `http://127.0.0.1:8000`.

`vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "services": {
    "api": {
      "root": "apps/api",
      "framework": "fastapi",
      "entrypoint": "app.main:app"
    },
    "web": {
      "root": "apps/web",
      "framework": "nextjs",
      "bindings": [
        {
          "type": "service",
          "service": "api",
          "format": "url",
          "env": "API_URL"
        }
      ]
    }
  },
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": {
        "service": "web"
      }
    }
  ]
}
```

Do **not** set `API_URL` yourself in Vercel environment variables. The binding owns it. Do not add a public rewrite for `/api/*` unless you intentionally want to expose FastAPI directly.

## Required Vercel environment variables

Set these per environment (Production/Preview/Development as appropriate):

| Variable | Value |
|---|---|
| `APP_ENV` | `production` |
| `APP_BASE_URL` | The public HTTPS URL of the deployment |
| `API_BASE_URL` | The same public HTTPS URL (metadata use) |
| `DATABASE_URL` | External managed PostgreSQL connection string |
| `SESSION_SECRET` | Long random secret |
| `PROVIDER_CREDENTIAL_KEY` | Fernet key for provider credentials |
| `UPLOAD_DIR` | `/tmp/feedesk-uploads` |
| `COOKIE_NAME` | `__Host-fd_session` |
| `COOKIE_SECURE` | `true` |
| `TRUST_FORWARDED_FOR` | `true` behind Vercel's proxy chain |
| `OCR_ENABLED` | `false` unless a Tesseract runtime is supplied |
| `MESSAGING_PROVIDER` | `fake` |
| `MESSAGING_ENABLED` | `false` |
| `MESSAGING_KILL_SWITCH` | `true` |
| `SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD` | One-time initial admin credentials |

Do not put live Rasel credentials in the repository. Live messaging remains blocked until G0/G4.

## Database setup

Vercel does not run the local PostgreSQL cluster. Use a managed PostgreSQL instance and run migrations/seed before serving traffic:

```bash
cd apps/api
alembic upgrade head
python -m app.seed
```

Vercel build/install does not run these automatically. If you want them in the Vercel build hook, add a reviewed `[tool.vercel.scripts]` build command; do not run destructive data operations there.

## Known Vercel limitations for this repository

- **Uploads are ephemeral.** `UPLOAD_DIR=/tmp/...` is per-function and temporary. Import source files can disappear after upload, breaking later source downloads. Production requires object storage (for example S3 or Vercel Blob) behind the existing `imports/storage.py` abstraction.
- **No Tesseract.** Vercel's Python runtime does not include the Tesseract binary or Arabic traineddata. Leave OCR disabled; scanned PDFs degrade to `SCANNED_PDF`.
- **No long-running messaging worker.** `app/worker.py` is a polling process, not an HTTP service. Vercel needs a separate cron/queue/worker strategy before messages can be processed there.
- **Database must be external.** The local `55432` PostgreSQL cluster is not part of the deployment.
- **Function limits.** The bridge sets a 60-second max duration. Large OCR/imports may exceed the plan's function limit.
- **Preview environments** need their own database and `APP_BASE_URL`; do not point previews at production data.

## Local verification

The bridge was verified against the running local stack:

- Login through `http://localhost:3000/api/v1/auth/login` returns `200` and sets `fd_session`.
- `/api/v1/auth/me` with the forwarded cookie returns `200`.
- Invalid credentials return the API's `401 INVALID_CREDENTIALS` envelope.
- Multipart upload (including a 2 MB PDF) returns `201`.
- Source download returns the original file with its content type.
- Browser login/dashboard/statements load with zero console errors.

This validates the bridge behavior, not Vercel's production build or service binding. Use `vercel dev -L` and a Preview deployment to verify the actual binding.
