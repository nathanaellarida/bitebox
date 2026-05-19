from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StaffModel:
    staff_id: int
    first_name: str
    last_name: str
    email: str
    role: str
    is_active: bool
    last_login: datetime | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
