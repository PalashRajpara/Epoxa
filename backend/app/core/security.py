import os
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from jose import jwt
from app.core.config import settings

SECRET_KEY = settings.SUPABASE_ANON_KEY or settings.SUPABASE_PUBLISHABLE_KEY or "epoxa-supervisor-secret-key-2026"
ALGORITHM = "HS256"

def get_password_hash(password: str) -> str:
    """Generates a secure PBKDF2-HMAC-SHA256 salted password hash."""
    salt = secrets.token_hex(16)
    iterations = 100_000
    hash_bytes = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations
    )
    hash_hex = hash_bytes.hex()
    return f"pbkdf2:sha256:{iterations}${salt}${hash_hex}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a stored PBKDF2-HMAC-SHA256 hash in constant time."""
    if not hashed_password or not hashed_password.startswith("pbkdf2:sha256:"):
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        meta, salt, stored_hash = parts
        iterations = int(meta.split(":")[-1])

        computed_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        computed_hex = computed_bytes.hex()
        return secrets.compare_digest(computed_hex, stored_hash)
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    to_encode.update({
        "exp": expire,
        "aud": settings.JWT_EXPECTED_AUDIENCE,
        "iss": "epoxa-auth"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
