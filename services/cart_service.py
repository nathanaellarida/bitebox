"""In-memory cart used by the New Order window.

Cart structure:
{
    cart_key (str): {
        'product_id': int,
        'product_name': str,
        'unit_price': float,    # base + options additional_price
        'quantity': int,
        'options': list[ {'option_name': str, 'additional_price': float} ],
        'line_total': float,
        'qty_on_hand': int,
    }
}
"""
from __future__ import annotations

from typing import Optional

from services.promotion_service import validate_promotion_code


class Cart:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}
        self.applied_promo: Optional[dict] = None  # validate result

    def _make_key(self, product_id: int, options: list[dict]) -> str:
        opt_part = "|".join(sorted(o["option_name"] for o in options))
        return f"{product_id}::{opt_part}"

    def add_item(
        self,
        product_id: int,
        product_name: str,
        base_price: float,
        qty_on_hand: int,
        quantity: int = 1,
        options: list[dict] | None = None,
    ) -> None:
        options = options or []
        unit_price = base_price + sum(float(o.get("additional_price", 0.0)) for o in options)
        key = self._make_key(product_id, options)
        if key in self.items:
            self.items[key]["quantity"] += quantity
        else:
            self.items[key] = {
                "product_id": product_id,
                "product_name": product_name,
                "unit_price": unit_price,
                "quantity": quantity,
                "options": options,
                "qty_on_hand": qty_on_hand,
            }
        self._recalc(key)

    def update_quantity(self, key: str, quantity: int) -> None:
        if key in self.items:
            self.items[key]["quantity"] = max(1, int(quantity))
            self._recalc(key)

    def remove_item(self, key: str) -> None:
        self.items.pop(key, None)

    def clear(self) -> None:
        self.items.clear()
        self.applied_promo = None

    def _recalc(self, key: str) -> None:
        line = self.items[key]
        line["line_total"] = round(line["unit_price"] * line["quantity"], 2)

    @property
    def subtotal(self) -> float:
        return round(sum(i["line_total"] for i in self.items.values()), 2)

    @property
    def discount_amount(self) -> float:
        return float(self.applied_promo["discount_amount"]) if self.applied_promo and self.applied_promo.get("is_valid") else 0.0

    @property
    def total(self) -> float:
        return round(max(self.subtotal - self.discount_amount, 0.0), 2)

    def apply_voucher(self, code: str) -> dict:
        result = validate_promotion_code(
            code,
            self.subtotal,
            [it["product_id"] for it in self.items.values()],
        )
        self.applied_promo = result if result["is_valid"] else None
        return result

    def remove_voucher(self) -> None:
        self.applied_promo = None
