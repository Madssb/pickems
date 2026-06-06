"""
Endpoints for the pickems frontend to consume.

Includes:
- POST: /login-links creates or rotates the current participant's login link
- GET: /login uses a reusable login link to create a browser session
- GET: /session returns the participant associated with this browser
- POST: /session creates an anonymous participant and browser session
- DELETE: /session deletes this browser session
- POST: /display-name updates the current participant's display name
- GET: /predictions returns saved predictions, or an empty prediction shape
- PUT: /predictions saves predictions before the deadline
"""
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from db import (
    create_participant_with_session,
    create_session,
    delete_session,
    get_participant_id_by_login_token_hash,
    get_participant_by_session_hash,
    get_predictions,
    update_display_name,
    upsert_login_token,
    upsert_predictions,
)
from fastapi import Request, Response, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from tokens import generate_token, hash_token


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS")
if not CORS_ALLOWED_ORIGINS:
    raise SystemExit("CORS_ALLOWED_ORIGINS is not set")

def require_http_base_url(env_name: str) -> str:
    value = os.getenv(env_name)
    if not value:
        raise SystemExit(f"{env_name} is not set")

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit(
            f"{env_name} must be an absolute http(s) URL, "
            "for example https://pickems-api.ladlorchart.com"
        )

    return value.rstrip("/")


BACKEND_BASE_URL = require_http_base_url("VITE_API_BASE_URL")

FRONTEND_BASE_URL = require_http_base_url("FRONTEND_BASE_URL")

APP_ENV = os.getenv("APP_ENV", "development")
if APP_ENV != "production":
    backend_hostname = urlparse(BACKEND_BASE_URL).hostname
    frontend_hostname = urlparse(FRONTEND_BASE_URL).hostname
    if backend_hostname != frontend_hostname:
        raise SystemExit(
            "VITE_API_BASE_URL and FRONTEND_BASE_URL must use the same hostname "
            "in development, for example localhost for both"
        )

allowed_origins = [
    origin.strip()
    for origin in CORS_ALLOWED_ORIGINS.split(",")
    if origin.strip()
]
if not allowed_origins:
    raise SystemExit("CORS_ALLOWED_ORIGINS must contain at least one origin")

app = FastAPI(title="Pickems API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREDICTION_DEADLINE = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def reject_after_prediction_deadline() -> None:
    if datetime.now(timezone.utc) >= PREDICTION_DEADLINE:
        raise HTTPException(status_code=403, detail="Predictions are closed")


class LoginLinkResponse(BaseModel):
    login_url: str

class SessionResponse(BaseModel):
    id: int
    display_name: str

class DisplayNameRequest(BaseModel):
    display_name: str

class PredictionsRequest(BaseModel):
    team_rankings: list[str] = Field(default_factory=list)
    first_kill: str | None = None
    first_death: str | None = None
    most_kills: str | None = None
    fewest_kills: str | None = None
    most_kills_team: str | None = None
    most_deaths: str | None = None
    most_deaths_team: str | None = None
    least_deaths_team: str | None = None
    first_fire_cape: str | None = None
    first_infernal_cape: str | None = None
    first_deep_delve: str | None = None
    first_voidwaker: str | None = None
    first_vls: str | None = None
    most_xp: str | None = None
    most_quest_points: str | None = None

class PredictionsResponse(BaseModel):
    message: str
    updated_at: datetime

@app.post("/login-links", response_model=LoginLinkResponse)
async def create_or_rotate_login_link(
    request: Request,
) -> LoginLinkResponse:
    """Create or rotate the participant's reusable login link."""
    session_token = request.cookies.get("session_token")
    if session_token is None:
        raise HTTPException(status_code=401, detail="No session")

    participant = await get_participant_by_session_hash(hash_token(session_token))
    if participant is None:
        raise HTTPException(status_code=401, detail="Invalid session")

    token, token_hash = generate_token()

    await upsert_login_token(participant["id"], token_hash)
    login_url = f"{BACKEND_BASE_URL}/login?token={token}"

    return LoginLinkResponse(login_url=login_url)


@app.get("/login")
async def login_with_token(token: str):
    """Use a reusable login token to create a new browser session."""
    token_hash = hash_token(token)
    participant_id = await get_participant_id_by_login_token_hash(token_hash)

    if participant_id is None:
        raise HTTPException(status_code=400, detail="Invalid login link")

    session_token, session_hash = generate_token()
    await create_session(session_hash, participant_id)

    response = RedirectResponse(FRONTEND_BASE_URL)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=APP_ENV == "production",
        samesite="lax",
        max_age=60 * 60 * 24 * 90,
    )
    return response


@app.delete("/session")
async def delete_browser_session(request: Request) -> JSONResponse:
    session_token = request.cookies.get("session_token")
    if session_token is not None:
        await delete_session(hash_token(session_token))

    response = JSONResponse({"message": "Session deleted"})
    response.delete_cookie(
        key="session_token",
        secure=APP_ENV == "production",
        samesite="lax",
    )
    return response


@app.post("/display-name", response_model=SessionResponse)
async def set_display_name(
    payload: DisplayNameRequest,
    request: Request,
) -> SessionResponse:
    """Update the current participant's display name."""
    display_name = payload.display_name.strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="Display name is required")

    session_token = request.cookies.get("session_token")
    if session_token is None:
        raise HTTPException(status_code=401, detail="No session")

    participant = await get_participant_by_session_hash(hash_token(session_token))
    if participant is None:
        raise HTTPException(status_code=401, detail="Invalid session")

    updated_participant = await update_display_name(participant["id"], display_name)
    return SessionResponse(**updated_participant)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.put("/predictions")
async def save_predictions(
    request: Request,
    predictions: PredictionsRequest,
) -> PredictionsResponse:
    """Save predictions for the current participant."""
    reject_after_prediction_deadline()
    session_token = request.cookies.get("session_token")
    if session_token is None:
        raise HTTPException(status_code=401, detail="No session")

    participant = await get_participant_by_session_hash(hash_token(session_token))
    if participant is None:
        raise HTTPException(status_code=401, detail="Invalid session")

    updated_at = await upsert_predictions(participant["id"], predictions.model_dump())
    return PredictionsResponse(
        message="Predictions saved",
        updated_at=updated_at,
    )


@app.get("/predictions", response_model=PredictionsRequest)
async def read_predictions(request: Request) -> PredictionsRequest:
    """Return predictions saved by the current participant."""
    session_token = request.cookies.get("session_token")
    if session_token is None:
        raise HTTPException(status_code=401, detail="No session")

    participant = await get_participant_by_session_hash(hash_token(session_token))
    if participant is None:
        raise HTTPException(status_code=401, detail="Invalid session")

    predictions = await get_predictions(participant["id"])
    if predictions is None:
        return PredictionsRequest()
    return PredictionsRequest(**predictions)
    

@app.post("/session", response_model=SessionResponse)
async def create_or_get_session(
    request: Request,
    response: Response,
) -> SessionResponse:
    """
    Return the existing participant when the cookie is valid; otherwise create
    an anonymous participant and browser session.
    """
    session_token = request.cookies.get("session_token")
    if session_token is not None:
        participant = await get_participant_by_session_hash(hash_token(session_token))
        if participant is not None:
            return SessionResponse(**participant)

    session_token, session_hash = generate_token()
    participant = await create_participant_with_session(session_hash)

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=APP_ENV == "production",
        samesite="lax",
        max_age=60 * 60 * 24 * 90,
    )
    return SessionResponse(**participant)


@app.get("/session", response_model=SessionResponse)
async def get_session(request: Request) -> SessionResponse:
    session_token = request.cookies.get("session_token")
    if session_token is None:
        raise HTTPException(status_code=401, detail="No session")

    participant = await get_participant_by_session_hash(hash_token(session_token))
    if participant is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    return SessionResponse(**participant)
