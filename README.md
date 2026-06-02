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
