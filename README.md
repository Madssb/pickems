# Dmm Allstars pickems webapp

Sign up with magic link sent by email, make predictions before events start, then submissions lock. view stats and leaderboards when stats become available.
Note that e-mails provided during login are hashed and not directly viewable by repo-owner (see request_link in main.py for how email is consumed and stored).

display names will be manually approved for appearing on leaderboards to prevent abuse

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
