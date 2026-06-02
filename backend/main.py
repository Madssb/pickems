import os
from pathlib import Path
from typing import Any

from db import get_or_create_user_id_by_email, instantiate_magic_token, consume_magic_link
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from tokens import generate_token, hash_token
import resend


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS")
if not CORS_ALLOWED_ORIGINS:
    raise SystemExit("CORS_ALLOWED_ORIGINS is not set")

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
if not RESEND_API_KEY:
    raise SystemExit("RESEND_API_KEY is not set")

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


class PlaceholderForm(BaseModel):
    form: dict[str, Any] = Field(default_factory=dict)

class LoginRequest(BaseModel):
    email: str

@app.post("/auth/request-link")
async def request_link(payload: LoginRequest):
    """instantiate login url, send to specified email
    """
    email = payload.email.lower()
    if APP_ENV != "production" and email not in dev_allowed_emails:
        raise HTTPException(status_code=403, detail="Email is not allowed in dev")

    user_id = await get_or_create_user_id_by_email(email)
    token, token_hash = generate_token()

    await instantiate_magic_token(user_id, token_hash)
    magic_link = f"http://localhost:8000/auth/verify?token={token}"
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
        r = resend.Emails.send({
            "from": "login@pickems.ladlorchart.com",
            "to": email,
            "subject": "Pickems login url",
            "html": html
        })
    except Exception as e:
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
    


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/users/{user_id}/forms")
def submit_placeholder_form(user_id: int, payload: PlaceholderForm) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "form": payload.form,
        "message": "Placeholder form received",
    }
