import os, time, bcrypt, jwt
from typing import Optional

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
JWT_TTL_SECONDS = 60 * 60 * 24  # 24 hours

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def check_password(password: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed)
    except Exception:
        return False

def create_token(user_id: int, email: str) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "email": email, "iat": now, "exp": now + JWT_TTL_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        return None

def parse_bearer(auth_header: str) -> Optional[str]:
    if not auth_header: return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None
