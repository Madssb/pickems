import secrets
import hashlib


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