"""Staff CRUD."""
from __future__ import annotations

import secrets
import string

from database.db_manager import session_scope
from database.models import Staff
from models.staff import StaffModel
from services.auth_service import hash_password


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


def list_staff() -> list[StaffModel]:
    with session_scope() as s:
        rows = s.query(Staff).order_by(Staff.first_name).all()
        return [_to_model(r) for r in rows]


def add_staff(
    first_name: str, last_name: str, email: str, role: str, password: str
) -> int:
    with session_scope() as s:
        st = Staff(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email.strip(),
            role=role,
            password_hash=hash_password(password),
        )
        s.add(st)
        s.flush()
        return st.staff_id


def update_staff(
    staff_id: int, first_name: str, last_name: str, email: str,
    role: str, is_active: bool
) -> None:
    with session_scope() as s:
        st = s.get(Staff, staff_id)
        if st:
            st.first_name = first_name.strip()
            st.last_name = last_name.strip()
            st.email = email.strip()
            st.role = role
            st.is_active = is_active


def delete_staff(staff_id: int) -> None:
    with session_scope() as s:
        st = s.get(Staff, staff_id)
        if st:
            s.delete(st)


def reset_password(staff_id: int) -> str:
    """Generate a new random password, hash it, return the plaintext."""
    alphabet = string.ascii_letters + string.digits
    new_pw = "".join(secrets.choice(alphabet) for _ in range(10))
    with session_scope() as s:
        st = s.get(Staff, staff_id)
        if st:
            st.password_hash = hash_password(new_pw)
    return new_pw
