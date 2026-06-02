# Pickems

## Quickstart

Serve the frontend locally with Vite:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at:

```text
http://127.0.0.1:5173
```

The frontend reads its backend URL from `VITE_API_BASE_URL` in the repo-root `.env` file:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
EMAIL_HASH_SECRET=replace-with-a-long-random-secret
```

Run the FastAPI backend with `uv`:

```bash
cd backend
uv sync
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Useful local endpoints:

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/users/123/forms \
  -H "Content-Type: application/json" \
  -d '{"form":{"example":"value"}}'
```

FastAPI docs are available at:

```text
http://127.0.0.1:8000/docs
```

## Email Privacy Migration

Existing databases that still have `users.email` can be migrated to
`users.email_hash` with:

```bash
psql "$DATABASE_URL" -v email_hash_secret="$EMAIL_HASH_SECRET" -f backend/migrations/001_store_email_hashes_only.sql
```
