"""Customer queries (creation/editing is handled by customer_auth_service)."""
from __future__ import annotations

from sqlalchemy import func, or_

from database.db_manager import session_scope
from database.models import Customer, Order
from models.customer import CustomerModel


def _to_model(c: Customer, total_orders: int = 0) -> CustomerModel:
    return CustomerModel(
        customer_id=c.customer_id,
        first_name=c.first_name,
        last_name=c.last_name,
        email=c.email,
        contact_number=c.contact_number,
        address=c.address,
        street=getattr(c, "street", None),
        city=getattr(c, "city", None),
        province=getattr(c, "province", None),
        postal_code=getattr(c, "postal_code", None),
        landmark=getattr(c, "landmark", None),
        is_active=bool(c.is_active) if c.is_active is not None else True,
        has_portal_account=bool(c.password_hash),
        created_at=c.created_at,
        total_orders=total_orders,
    )


def list_customers(search: str = "", include_inactive: bool = True) -> list[CustomerModel]:
    with session_scope() as s:
        q = s.query(Customer)
        if not include_inactive:
            q = q.filter(Customer.is_active.is_(True))
        if search:
            like = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    Customer.first_name.ilike(like),
                    Customer.last_name.ilike(like),
                    Customer.email.ilike(like),
                )
            )
        rows = q.order_by(Customer.first_name).all()
        result: list[CustomerModel] = []
        for c in rows:
            count = (
                s.query(func.count(Order.order_id))
                .filter(Order.customer_id == c.customer_id)
                .scalar()
            )
            result.append(_to_model(c, int(count or 0)))
        return result


def get_customer(customer_id: int) -> CustomerModel | None:
    with session_scope() as s:
        c = s.get(Customer, customer_id)
        if not c:
            return None
        count = (
            s.query(func.count(Order.order_id))
            .filter(Order.customer_id == c.customer_id)
            .scalar()
        )
        return _to_model(c, int(count or 0))


def deactivate_customer(customer_id: int) -> None:
    with session_scope() as s:
        c = s.get(Customer, customer_id)
        if c:
            c.is_active = False


def reactivate_customer(customer_id: int) -> None:
    with session_scope() as s:
        c = s.get(Customer, customer_id)
        if c:
            c.is_active = True


def update_profile(
    customer_id: int, first_name: str, last_name: str,
    contact_number: str | None = None, address: str | None = None,
    street: str | None = None, city: str | None = None,
    province: str | None = None, postal_code: str | None = None,
    landmark: str | None = None,
) -> None:
    """Self-service profile update from the customer portal. Email is immutable."""
    with session_scope() as s:
        c = s.get(Customer, customer_id)
        if c:
            c.first_name = first_name.strip()
            c.last_name = last_name.strip()
            c.contact_number = (contact_number or "").strip() or None
            c.address = (address or "").strip() or None
            c.street = (street or "").strip() or None
            c.city = (city or "").strip() or None
            c.province = (province or "").strip() or None
            c.postal_code = (postal_code or "").strip() or None
            c.landmark = (landmark or "").strip() or None
