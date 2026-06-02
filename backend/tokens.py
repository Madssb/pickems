import secrets
import hashlib
import hmac


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_email(email: str, secret: str) -> str:
    return hmac.new(
        secret.encode(),
        normalize_email(email).encode(),
        hashlib.sha256,
    ).hexdigest()


def generate_token():
    """Generate a token and its hash
    """
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(
        token.encode()
    ).hexdigest()
    return token, token_hash

def hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode()
    ).hexdigest()


def generate_session_id() -> str:
    return secrets.token_urlsafe(32)
