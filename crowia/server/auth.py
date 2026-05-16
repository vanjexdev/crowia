"""Auth module — bcrypt + JWT. Only active when server.auth.enabled: true."""
import datetime
import secrets

import bcrypt
import jwt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_token(username: str, secret: str, expire_hours: int) -> str:
    payload = {
        "sub": username,
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(hours=expire_hours),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_token(token: str, secret: str) -> str | None:
    """Return username if valid, None otherwise."""
    try:
        data = jwt.decode(token, secret, algorithms=["HS256"])
        return data.get("sub")
    except jwt.PyJWTError:
        return None


def random_secret(n: int = 32) -> str:
    return secrets.token_hex(n)
