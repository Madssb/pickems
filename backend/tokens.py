import secrets
import hashlib
def generate_token() -> tuple[str, str]:
    """Generate a secret token and its SHA-256 hash."""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(
        token.encode()
    ).hexdigest()
    return token, token_hash

def hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode()
    ).hexdigest()
