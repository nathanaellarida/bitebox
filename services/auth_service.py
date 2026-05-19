"""Authentication and password hashing."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import bcrypt

from database.db_manager import session_scope
from database.models import Staff
from models.staff import StaffModel


def _to_model(s: Staff) -> StaffModel:
    return StaffModel(
        staff_id=s.staff_id,
        first_name=s.first_name,
        last_name=s.last_name,
        email=s.email,
        role=s.role,
        is_active=s.is_active,
        last_login=s.last_login,
    )


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def login(email: str, password: str) -> Optional[StaffModel]:
    """Returns StaffModel if successful, else None."""
    with session_scope() as s:
        user = s.query(Staff).filter(Staff.email == email.strip()).first()
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        user.last_login = datetime.now()
        s.flush()
        return _to_model(user)
