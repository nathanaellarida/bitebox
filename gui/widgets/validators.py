"""Reusable input validators for forms across the application.

Each validator returns ``None`` when the value is acceptable, or a short
human-readable error message when it is not. Forms can collect errors
from several validators before showing them to the user.

The helpers also include a small ``mark_error / clear_error`` pair that
toggles a red outline on a QLineEdit / QTextEdit / QComboBox via a
dynamic ``error`` property so QSS can style it consistently.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Iterable

from PyQt6.QtWidgets import QWidget


# ---------- Regex patterns ----------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[+\d][\d\-\s]{6,19}$")
NAME_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ' .\-]{1,60}$")
POSTAL_RE = re.compile(r"^\d{4,10}$")
PROMO_CODE_RE = re.compile(r"^[A-Z0-9_\-]{3,20}$")


# ---------- Field validators ----------

def required(value: str | None, label: str) -> str | None:
    if not (value or "").strip():
        return f"{label} is required."
    return None


def text_length(value: str | None, label: str, *, minimum: int = 1,
                maximum: int = 255) -> str | None:
    v = (value or "").strip()
    if len(v) < minimum:
        return f"{label} must be at least {minimum} characters."
    if len(v) > maximum:
        return f"{label} must be at most {maximum} characters."
    return None


def email(value: str | None, label: str = "Email") -> str | None:
    v = (value or "").strip()
    if not v:
        return f"{label} is required."
    if not EMAIL_RE.match(v):
        return f"{label} doesn't look like a valid email address."
    if len(v) > 254:
        return f"{label} is too long."
    return None


def name(value: str | None, label: str) -> str | None:
    v = (value or "").strip()
    if not v:
        return f"{label} is required."
    if len(v) > 60:
        return f"{label} must be at most 60 characters."
    if not NAME_RE.match(v):
        return f"{label} contains invalid characters."
    return None


def phone(value: str | None, label: str = "Contact number",
          *, optional: bool = False) -> str | None:
    v = (value or "").strip()
    if not v:
        return None if optional else f"{label} is required."
    if not PHONE_RE.match(v):
        return f"{label} must be 7–20 digits, optionally with +, spaces or dashes."
    return None


def postal_code(value: str | None, label: str = "Postal code",
                *, optional: bool = False) -> str | None:
    v = (value or "").strip()
    if not v:
        return None if optional else f"{label} is required."
    if not POSTAL_RE.match(v):
        return f"{label} must be 4–10 digits."
    return None


def password_strength(value: str, label: str = "Password") -> str | None:
    if len(value) < 8:
        return f"{label} must be at least 8 characters."
    if not re.search(r"[A-Z]", value):
        return f"{label} must contain at least one uppercase letter."
    if not re.search(r"[a-z]", value):
        return f"{label} must contain at least one lowercase letter."
    if not re.search(r"\d", value):
        return f"{label} must contain at least one digit."
    if len(value) > 128:
        return f"{label} is too long."
    return None


def passwords_match(p1: str, p2: str) -> str | None:
    if p1 != p2:
        return "Passwords do not match."
    return None


def positive_number(value: float, label: str, *, allow_zero: bool = False,
                    maximum: float | None = None) -> str | None:
    if value is None:
        return f"{label} is required."
    if allow_zero:
        if value < 0:
            return f"{label} cannot be negative."
    else:
        if value <= 0:
            return f"{label} must be greater than 0."
    if maximum is not None and value > maximum:
        return f"{label} must be {maximum:g} or less."
    return None


def positive_int(value: int, label: str, *, allow_zero: bool = True,
                 maximum: int | None = None) -> str | None:
    if value is None:
        return f"{label} is required."
    if allow_zero:
        if value < 0:
            return f"{label} cannot be negative."
    else:
        if value <= 0:
            return f"{label} must be greater than 0."
    if maximum is not None and value > maximum:
        return f"{label} must be {maximum} or less."
    return None


def promo_code(value: str | None, label: str = "Promo code") -> str | None:
    v = (value or "").strip().upper()
    if not v:
        return f"{label} is required."
    if not PROMO_CODE_RE.match(v):
        return (f"{label} must be 3–20 characters, "
                "letters, digits, dashes, or underscores only.")
    return None


def date_range(start: date | datetime | None,
               end: date | datetime | None) -> str | None:
    if start and end and start > end:
        return "Start date must be on or before the end date."
    return None


def luhn_valid(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 13:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def credit_card(value: str | None, label: str = "Card number") -> str | None:
    v = (value or "").replace(" ", "").replace("-", "")
    if not v:
        return f"{label} is required."
    if not v.isdigit():
        return f"{label} must contain digits only."
    if not 13 <= len(v) <= 19:
        return f"{label} must be 13–19 digits."
    if not luhn_valid(v):
        return f"{label} failed the Luhn checksum."
    return None


def card_expiry(value: str | None, label: str = "Expiry") -> str | None:
    v = (value or "").strip()
    if not v:
        return f"{label} is required."
    if not re.match(r"^(0[1-9]|1[0-2])/\d{2}$", v):
        return f"{label} must be in MM/YY format (e.g. 09/27)."
    month, year = int(v[:2]), int(v[3:])
    today = date.today()
    full_year = 2000 + year
    last_day = (date(full_year + (1 if month == 12 else 0),
                     1 if month == 12 else month + 1, 1))
    if last_day <= today:
        return f"{label} is in the past."
    return None


def card_cvv(value: str | None, label: str = "CVV") -> str | None:
    v = (value or "").strip()
    if not v:
        return f"{label} is required."
    if not (v.isdigit() and 3 <= len(v) <= 4):
        return f"{label} must be 3 or 4 digits."
    return None


def gcash_number(value: str | None, label: str = "GCash number") -> str | None:
    v = (value or "").replace(" ", "").replace("-", "")
    if not v:
        return f"{label} is required."
    if not v.isdigit():
        return f"{label} must contain digits only."
    if not 10 <= len(v) <= 13:
        return f"{label} must be 10–13 digits."
    return None


# ---------- Aggregation helper ----------

def first_error(*errors: str | None) -> str | None:
    """Return the first non-None error from a sequence of validator results."""
    for e in errors:
        if e:
            return e
    return None


def collect_errors(*errors: str | None) -> list[str]:
    """Return only the non-None error messages."""
    return [e for e in errors if e]


# ---------- Visual error markers ----------

_ERROR_QSS = (
    "QLineEdit[error=\"true\"], QTextEdit[error=\"true\"],"
    "QComboBox[error=\"true\"], QSpinBox[error=\"true\"],"
    "QDoubleSpinBox[error=\"true\"], QDateEdit[error=\"true\"]"
    "{ border:1.5px solid #EF4444; }"
)


def install_error_qss(widget: QWidget) -> None:
    """Append the shared error-state stylesheet to ``widget``.

    Call once on the top-level dialog/window so the red outline applies
    to every input inside it.
    """
    existing = widget.styleSheet() or ""
    if _ERROR_QSS in existing:
        return
    widget.setStyleSheet(existing + "\n" + _ERROR_QSS)


def mark_error(widget: QWidget, on: bool = True) -> None:
    """Toggle the dynamic ``error`` property used by the QSS above."""
    widget.setProperty("error", "true" if on else "false")
    style = widget.style()
    if style:
        style.unpolish(widget)
        style.polish(widget)


def clear_errors(widgets: Iterable[QWidget]) -> None:
    for w in widgets:
        mark_error(w, False)
