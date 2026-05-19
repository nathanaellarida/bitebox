from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


@dataclass
class PromotionModel:
    promotion_id: int
    promotion_name: str
    promotion_description: str | None
    discount_type: str  # "Percentage" | "FixedAmount"
    discount_value: float
    minimum_order_amount: float
    code: str
    usage_limit: int | None
    used_count: int
    start_date: date | None
    end_date: date | None
    is_active: bool
    product_ids: list[int] = field(default_factory=list)
