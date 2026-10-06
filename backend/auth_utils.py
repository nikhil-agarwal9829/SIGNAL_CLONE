import secrets
import hashlib
from datetime import datetime, timedelta, timezone

def generate_session_token() -> str:
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def get_expires_at(days=30) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)
