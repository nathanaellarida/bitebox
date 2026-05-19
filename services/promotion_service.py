"""Promotion / discount-code CRUD and validation."""
from __future__ import annotations

from datetime import date
from typing import Optional

from database.db_manager import session_scope
from database.models import Promotion, PromotionProduct
from models.promotion import PromotionModel


def _to_model(p: Promotion, product_ids: list[int]) -> PromotionModel:
    return PromotionModel(
        promotion_id=p.promotion_id,
        promotion_name=p.promotion_name,
        promotion_description=p.promotion_description,
        discount_type=p.discount_type,
        discount_value=p.discount_value,
        minimum_order_amount=p.minimum_order_amount,
        code=p.code,
        usage_limit=p.usage_limit,
        used_count=p.used_count,
        start_date=p.start_date,
        end_date=p.end_date,
        is_active=p.is_active,
        product_ids=product_ids,
    )


def list_promotions() -> list[PromotionModel]:
    with session_scope() as s:
        rows = s.query(Promotion).order_by(Promotion.promotion_name).all()
        result = []
        for p in rows:
            pids = [
                pp.product_id
                for pp in s.query(PromotionProduct).filter_by(promotion_id=p.promotion_id).all()
            ]
            result.append(_to_model(p, pids))
        return result


def add_promotion(
    name: str, description: str, discount_type: str, discount_value: float,
    minimum_order_amount: float, code: str, usage_limit: Optional[int],
    start_date: Optional[date], end_date: Optional[date], is_active: bool,
    product_ids: list[int],
) -> int:
    with session_scope() as s:
        p = Promotion(
            promotion_name=name.strip(),
            promotion_description=description,
            discount_type=discount_type,
            discount_value=float(discount_value),
            minimum_order_amount=float(minimum_order_amount),
            code=code.strip(),
            usage_limit=usage_limit,
            start_date=start_date,
            end_date=end_date,
            is_active=is_active,
        )
        s.add(p)
        s.flush()
        for pid in product_ids:
            s.add(PromotionProduct(promotion_id=p.promotion_id, product_id=pid))
        return p.promotion_id


def update_promotion(
    promotion_id: int, name: str, description: str, discount_type: str,
    discount_value: float, minimum_order_amount: float, code: str,
    usage_limit: Optional[int], start_date: Optional[date],
    end_date: Optional[date], is_active: bool, product_ids: list[int],
) -> None:
    with session_scope() as s:
        p = s.get(Promotion, promotion_id)
        if not p:
            return
        p.promotion_name = name.strip()
        p.promotion_description = description
        p.discount_type = discount_type
        p.discount_value = float(discount_value)
        p.minimum_order_amount = float(minimum_order_amount)
        p.code = code.strip()
        p.usage_limit = usage_limit
        p.start_date = start_date
        p.end_date = end_date
        p.is_active = is_active
        s.query(PromotionProduct).filter_by(promotion_id=promotion_id).delete()
        for pid in product_ids:
            s.add(PromotionProduct(promotion_id=promotion_id, product_id=pid))


def delete_promotion(promotion_id: int) -> None:
    with session_scope() as s:
        s.query(PromotionProduct).filter_by(promotion_id=promotion_id).delete()
        p = s.get(Promotion, promotion_id)
        if p:
            s.delete(p)


def validate_promotion_code(
    code: str, cart_total: float, product_ids_in_cart: list[int]
) -> dict:
    """
    Returns: { is_valid: bool, discount_amount: float, message: str,
               promotion_id: int|None, code: str }
    """
    if not code:
        return {"is_valid": False, "discount_amount": 0.0, "message": "Empty code", "promotion_id": None, "code": ""}
    today = date.today()
    with session_scope() as s:
        p: Promotion | None = s.query(Promotion).filter(Promotion.code == code.strip()).first()
        if not p:
            return {"is_valid": False, "discount_amount": 0.0, "message": "Code not found", "promotion_id": None, "code": code}
        if not p.is_active:
            return {"is_valid": False, "discount_amount": 0.0, "message": "Code is inactive", "promotion_id": p.promotion_id, "code": code}
        if p.start_date and today < p.start_date:
            return {"is_valid": False, "discount_amount": 0.0, "message": "Code not yet started", "promotion_id": p.promotion_id, "code": code}
        if p.end_date and today > p.end_date:
            return {"is_valid": False, "discount_amount": 0.0, "message": "Code expired", "promotion_id": p.promotion_id, "code": code}
        if p.usage_limit is not None and p.used_count >= p.usage_limit:
            return {"is_valid": False, "discount_amount": 0.0, "message": "Usage limit reached", "promotion_id": p.promotion_id, "code": code}
        if cart_total < p.minimum_order_amount:
            return {
                "is_valid": False,
                "discount_amount": 0.0,
                "message": f"Minimum order ₱{p.minimum_order_amount:.2f} required",
                "promotion_id": p.promotion_id,
                "code": code,
            }
        # product-specific check
        scoped_pids = [
            pp.product_id
            for pp in s.query(PromotionProduct).filter_by(promotion_id=p.promotion_id).all()
        ]
        if scoped_pids and not any(pid in scoped_pids for pid in product_ids_in_cart):
            return {
                "is_valid": False,
                "discount_amount": 0.0,
                "message": "Code does not apply to any product in cart",
                "promotion_id": p.promotion_id,
                "code": code,
            }

        if p.discount_type == "Percentage":
            discount = round(cart_total * (p.discount_value / 100.0), 2)
        else:
            discount = round(min(p.discount_value, cart_total), 2)

        return {
            "is_valid": True,
            "discount_amount": discount,
            "message": f"Discount applied: ₱{discount:.2f}",
            "promotion_id": p.promotion_id,
            "code": code,
        }


def increment_usage(promotion_id: int) -> None:
    with session_scope() as s:
        p = s.get(Promotion, promotion_id)
        if p:
            p.used_count += 1


def get_active_promotions() -> list[PromotionModel]:
    """Return promotions that are usable right now (active, in date
    range, under usage limit). Used by the customer portal for hints.
    """
    today = date.today()
    out: list[PromotionModel] = []
    for p in list_promotions():
        if not p.is_active:
            continue
        if p.start_date and today < p.start_date:
            continue
        if p.end_date and today > p.end_date:
            continue
        if p.usage_limit is not None and p.used_count >= p.usage_limit:
            continue
        out.append(p)
    return out
