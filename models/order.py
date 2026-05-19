from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class OrderItemOptionModel:
    option_name: str
    additional_price: float = 0.0


@dataclass
class OrderItemModel:
    order_item_id: int
    product_id: int | None
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float
    options: list[OrderItemOptionModel] = field(default_factory=list)


@dataclass
class OrderStatusHistoryEntry:
    from_status: str | None
    to_status: str
    changed_by: str | None
    notes: str | None
    created_at: datetime


@dataclass
class OrderModel:
    order_id: int
    customer_id: int | None
    customer_name: str
    customer_email: str
    staff_id: int | None
    staff_name: str
    order_date: datetime
    subtotal: float
    discount_amount: float
    total_amount: float
    order_type: str
    order_status: str
    payment_method: str | None
    payment_status: str
    voucher_code: str | None
    delivery_notes: str | None
    email_sent_to: str | None
    email_sent_at: datetime | None
    items: list[OrderItemModel] = field(default_factory=list)
    history: list[OrderStatusHistoryEntry] = field(default_factory=list)
