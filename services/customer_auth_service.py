"""Customer (portal) authentication and registration."""
from __future__ import annotations

import re
from typing import Optional, Union

import bcrypt

from database.db_manager import session_scope
from database.models import Customer
from models.customer import CustomerModel
from services.customer_service import _to_model

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_password(pw: str) -> str | None:
    if len(pw) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", pw):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"\d", pw):
        return "Password must contain at least one digit."
    return None


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def register(
    first_name: str, last_name: str, email: str, password: str,
    contact_number: Optional[str] = None, address: Optional[str] = None,
    street: Optional[str] = None, city: Optional[str] = None,
    province: Optional[str] = None, postal_code: Optional[str] = None,
    landmark: Optional[str] = None,
) -> Union[CustomerModel, str]:
    """
    Create a new customer account. Returns CustomerModel on success or an
    error string on failure (caller displays it).

    Both the legacy free-form ``address`` field and the structured address
    fields (``street``, ``city``, ``province``, ``postal_code``, ``landmark``)
    are accepted. The legacy field is auto-derived from the structured ones
    when the caller doesn't supply it, so the data stays consistent.
    """
    if not (first_name.strip() and last_name.strip() and email.strip()):
        return "First name, last name, and email are required."
    if not EMAIL_RE.match(email.strip()):
        return "Please enter a valid email address."
    pw_err = _validate_password(password)
    if pw_err:
        return pw_err

    # Normalize structured address fields once.
    street_v = (street or "").strip() or None
    city_v = (city or "").strip() or None
    province_v = (province or "").strip() or None
    postal_v = (postal_code or "").strip() or None
    landmark_v = (landmark or "").strip() or None

    # Compose a legacy free-form address from the structured fields when the
    # caller didn't pass one explicitly. Keeps older code paths working.
    legacy_address = (address or "").strip()
    if not legacy_address:
        parts = [p for p in (street_v, city_v, province_v, postal_v) if p]
        legacy_address = ", ".join(parts)
        if landmark_v:
            legacy_address = (
                f"{legacy_address} ({landmark_v})" if legacy_address else landmark_v
            )
    address_v: Optional[str] = legacy_address or None

    email_norm = email.strip().lower()
    with session_scope() as s:
        existing = s.query(Customer).filter(Customer.email == email_norm).first()
        if existing:
            if existing.password_hash:
                return "An account with this email already exists."
            # Walk-in record promoted to a portal account
            existing.first_name = first_name.strip()
            existing.last_name = last_name.strip()
            existing.contact_number = (contact_number or "").strip() or None
            existing.address = address_v
            existing.street = street_v
            existing.city = city_v
            existing.province = province_v
            existing.postal_code = postal_v
            existing.landmark = landmark_v
            existing.password_hash = _hash(password)
            existing.is_active = True
            s.flush()
            return _to_model(existing, 0)

        c = Customer(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email_norm,
            contact_number=(contact_number or "").strip() or None,
            address=address_v,
            street=street_v,
            city=city_v,
            province=province_v,
            postal_code=postal_v,
            landmark=landmark_v,
            password_hash=_hash(password),
            is_active=True,
        )
        s.add(c)
        s.flush()
        return _to_model(c, 0)


def login(email: str, password: str) -> Optional[CustomerModel]:
    """Authenticate a customer; returns CustomerModel or None."""
    with session_scope() as s:
        c = s.query(Customer).filter(Customer.email == email.strip().lower()).first()
        if not c or not c.password_hash:
            return None
        if not c.is_active:
            return None
        if not _verify(password, c.password_hash):
            return None
        return _to_model(c, 0)


def change_password(customer_id: int, current_pw: str, new_pw: str) -> str | None:
    """Returns None on success, or an error message."""
    err = _validate_password(new_pw)
    if err:
        return err
    with session_scope() as s:
        c = s.get(Customer, customer_id)
        if not c or not c.password_hash:
            return "Account not found."
        if not _verify(current_pw, c.password_hash):
            return "Current password is incorrect."
        c.password_hash = _hash(new_pw)
        return None
