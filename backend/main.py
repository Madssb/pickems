"""
Endpoints for the pickems frontend to consume.

Includes:
- POST: /auth/request-link generates and sends a login link per email
- GET: /auth/verify consumes a magic link, sets a session cookie, and redirects
- GET: /auth/me validates the session cookie and returns current user info
- POST: /auth/logout deletes the current session and clears the session cookie
- POST: /submit-predictions saves user predictions before the deadline
- GET: /get-predictions returns saved predictions, or an empty prediction shape
"""
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from db import (
    consume_magic_link,
    create_session,
    delete_session,
    get_or_create_user_id_by_email_hash,
    get_user_predictions,
    get_user_by_session,
    instantiate_magic_token,
    get_user_id_by_session_id,
    upsert_submission,
)
from fastapi import Request, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from tokens import generate_session_id, generate_token, hash_email, hash_token, normalize_email
import resend


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS")
if not CORS_ALLOWED_ORIGINS:
    raise SystemExit("CORS_ALLOWED_ORIGINS is not set")

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
if not RESEND_API_KEY:
    raise SystemExit("RESEND_API_KEY is not set")
resend.api_key = RESEND_API_KEY

EMAIL_HASH_SECRET = os.getenv("EMAIL_HASH_SECRET")
if not EMAIL_HASH_SECRET:
    raise SystemExit("EMAIL_HASH_SECRET is not set")

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
DEV_ALLOWED_EMAILS = os.getenv("DEV_ALLOWED_EMAILS", "")
dev_allowed_emails = {
    email.strip().lower()
    for email in DEV_ALLOWED_EMAILS.split(",")
    if email.strip()
}
if APP_ENV != "production" and not dev_allowed_emails:
    raise SystemExit("DEV_ALLOWED_EMAILS is not set")

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

SUBMISSION_DEADLINE = datetime(2026, 6, 6, 13, 0, tzinfo=timezone.utc)


def reject_after_submission_deadline() -> None:
    if datetime.now(timezone.utc) >= SUBMISSION_DEADLINE:
        raise HTTPException(status_code=403, detail="Submissions are closed")


class PlaceholderForm(BaseModel):
    form: dict[str, Any] = Field(default_factory=dict)

class LoginRequest(BaseModel):
    email: str
    display_name: str

class CurrentUserResponse(BaseModel):
    id: int
    display_name: str

class SubmissionRequest(BaseModel):
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

class SubmissionResponse(BaseModel):
    message: str
    updated_at: datetime

@app.post("/auth/request-link")
async def request_link(payload: LoginRequest):
    """instantiate login url, send to specified email
    """
    email = normalize_email(payload.email)
    if APP_ENV != "production" and email not in dev_allowed_emails:
        raise HTTPException(status_code=403, detail="Email is not allowed in dev")

    display_name = payload.display_name.strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="Display name is required")

    email_hash = hash_email(email, EMAIL_HASH_SECRET)
    user_id = await get_or_create_user_id_by_email_hash(email_hash, display_name)
    token, token_hash = generate_token()

    await instantiate_magic_token(user_id, token_hash)
    magic_link = f"{BACKEND_BASE_URL}/auth/verify?token={token}"
    html = f"""
    <p>Hi,</p>

    <p>Use this link to log in to DMM All Stars Pickems:</p>

    <p>
    <a href="{magic_link}">Log in to DMM All Stars Pickems</a>
    </p>

    <p>This link expires in 24 hours and can only be used once.</p>

    <p>If you did not request this, you can ignore this email.</p>
    """
    try:
        resend.Emails.send({
            "from": "login@pickems.ladlorchart.com",
            "to": email,
            "subject": "Pickems login url",
            "html": html
        })
    except Exception:
        raise Exception
    return {
        "message": "Login link requested",
    }


@app.get("/auth/verify")
async def verify(token: str):
    """Handle login request with token passed through email link
    """
    token_hash = hash_token(token)
    user_id = await consume_magic_link(token_hash)

    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired login link")

    session_id = generate_session_id()
    await create_session(session_id, user_id)

    response = RedirectResponse(FRONTEND_BASE_URL)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=APP_ENV == "production",
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


@app.get("/auth/me", response_model=CurrentUserResponse)
async def validate_session(request: Request) -> CurrentUserResponse:
    """
    """
    session_id = request.cookies.get("session_id")
    if session_id is None:
        raise HTTPException(status_code=401, detail="Not logged in")

    user = await get_user_by_session(session_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    return CurrentUserResponse(**user)


@app.post("/auth/logout")
async def logout(request: Request) -> JSONResponse:
    session_id = request.cookies.get("session_id")
    if session_id is not None:
        await delete_session(session_id)

    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie(
        key="session_id",
        secure=APP_ENV == "production",
        samesite="lax",
    )
    return response


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/submit-predictions")
async def submit_predictions(
    request: Request,
    predictions: SubmissionRequest,
) -> SubmissionResponse:
    """Submit user submitted dmma predictions
    """
    reject_after_submission_deadline()
    session_id = request.cookies.get("session_id")
    if session_id is None:
        raise HTTPException(status_code=401, detail="Not logged in")
    user_id = await get_user_id_by_session_id(session_id)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid session")

    updated_at = await upsert_submission(user_id, predictions.model_dump())
    return SubmissionResponse(
        message="Submission saved",
        updated_at=updated_at,
    )


@app.get("/get-predictions", response_model=SubmissionRequest)
async def get_predictions(request: Request) -> SubmissionRequest:
    """get user submitted dmma predictiosn if they exist
    """
    session_id = request.cookies.get("session_id")
    if session_id is None:
        raise HTTPException(status_code=401, detail="Not logged in")
    user_id = await get_user_id_by_session_id(session_id)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    predictions = await get_user_predictions(user_id)
    if predictions is None:
        return SubmissionRequest()
    return SubmissionRequest(**predictions)
    
