from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CustomerModel:
    customer_id: int
    first_name: str
    last_name: str
    email: str
    contact_number: str | None = None
    address: str | None = None
    # Structured delivery address; all optional. When empty the legacy
    # `address` field may still hold free-form text.
    street: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
    landmark: str | None = None
    is_active: bool = True
    has_portal_account: bool = False
    created_at: datetime | None = None
    total_orders: int = 0

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def has_delivery_address(self) -> bool:
        """True when the structured address is fully populated."""
        return all([
            (self.street or "").strip(),
            (self.city or "").strip(),
            (self.province or "").strip(),
            (self.postal_code or "").strip(),
        ])
