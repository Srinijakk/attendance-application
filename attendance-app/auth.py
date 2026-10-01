import bcrypt
from fastapi import Request
from database import db


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def get_user(request: Request):
    """Return the logged-in user row (from the signed session) or None."""
    uid = request.session.get("user_id")
    if not uid:
        return None
    with db() as c:
        return c.execute("SELECT * FROM employees WHERE id=?", (uid,)).fetchone()
