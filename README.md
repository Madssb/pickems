# DMM All Stars Pickems

Visitors receive an anonymous browser session automatically and can immediately
make predictions. Picks autosave until the prediction deadline.

Participants can create a login link that connects other browsers to the same
picks. No email address or account is required.

The current login link is a reusable bearer credential: anyone with it can
access the associated picks. Creating another login link rotates it and
immediately invalidates the previous link. Existing browser sessions remain
active.

The active API is organized around sessions, login links, and predictions:

```text
GET /session
POST /session
DELETE /session
POST /display-name
POST /login-links
GET /login
GET /predictions
PUT /predictions
```

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
