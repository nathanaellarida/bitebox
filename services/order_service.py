"""Order placement, status updates, history audit trail."""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import or_

from database.db_manager import session_scope
from database.models import (
    Customer, Order, OrderItem, OrderItemOption, OrderStatusHistory,
    PaymentLog, Product, Staff
)
from models.order import (
    OrderItemModel, OrderItemOptionModel, OrderModel, OrderStatusHistoryEntry
)
from services import promotion_service

ORDER_STATUSES = [
    "Pending", "Processing", "ReadyForPickup", "ReadyForDelivery",
    "Completed", "Cancelled",
]

# Allowed forward transitions. Cancel can happen from any non-terminal state.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "Pending": {"Processing", "ReadyForPickup", "ReadyForDelivery", "Completed", "Cancelled"},
    "Processing": {"ReadyForPickup", "ReadyForDelivery", "Completed", "Cancelled"},
    "ReadyForPickup": {"Completed", "Cancelled"},
    "ReadyForDelivery": {"Completed", "Cancelled"},
    "Completed": set(),
    "Cancelled": set(),
}


def _row_to_model(o: Order, history_rows: list[OrderStatusHistory] | None = None) -> OrderModel:
    customer_name = ""
    customer_email = ""
    if o.customer:
        customer_name = f"{o.customer.first_name} {o.customer.last_name}".strip()
        customer_email = o.customer.email
    staff_name = ""
    if o.staff:
        staff_name = f"{o.staff.first_name} {o.staff.last_name}".strip()
    items = [
        OrderItemModel(
            order_item_id=it.order_item_id,
            product_id=it.product_id,
            product_name=it.product_name,
            quantity=it.quantity,
            unit_price=it.unit_price,
            subtotal=it.subtotal,
            options=[
                OrderItemOptionModel(option_name=op.option_name, additional_price=op.additional_price)
                for op in it.options
            ],
        )
        for it in o.items
    ]
    history = [
        OrderStatusHistoryEntry(
            from_status=h.from_status,
            to_status=h.to_status,
            changed_by=h.changed_by,
            notes=h.notes,
            created_at=h.created_at,
        )
        for h in (history_rows or [])
    ]
    return OrderModel(
        order_id=o.order_id,
        customer_id=o.customer_id,
        customer_name=customer_name,
        customer_email=customer_email,
        staff_id=o.staff_id,
        staff_name=staff_name,
        order_date=o.order_date,
        subtotal=o.subtotal,
        discount_amount=o.discount_amount,
        total_amount=o.total_amount,
        order_type=o.order_type,
        order_status=o.order_status,
        payment_method=o.payment_method,
        payment_status=o.payment_status,
        voucher_code=o.voucher_code,
        delivery_notes=o.delivery_notes,
        email_sent_to=o.email_sent_to,
        email_sent_at=o.email_sent_at,
        items=items,
        history=history,
    )


def _log_history(session, order_id: int, from_status: str | None, to_status: str,
                 actor: str | None = None, notes: str | None = None) -> None:
    session.add(
        OrderStatusHistory(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=actor,
            notes=notes,
        )
    )


def get_allowed_next_statuses(current: str) -> list[str]:
    """Return the list of statuses the order can transition to from `current`."""
    return [s for s in ORDER_STATUSES if s in _ALLOWED_TRANSITIONS.get(current, set())]


def place_order(
    customer_id: int | None,
    staff_id: int | None,
    cart_items: dict,
    order_type: str,
    payment_method: str,
    delivery_notes: str = "",
    voucher_code: Optional[str] = None,
    discount_amount: float = 0.0,
    promotion_id: Optional[int] = None,
    actor_name: str | None = None,
) -> int:
    """
    Persist a new order. Validates stock, deducts qty_on_hand, increments qty_sold,
    and logs the initial 'Pending' state in the audit trail.
    """
    if not cart_items:
        raise ValueError("Cart is empty.")
    with session_scope() as s:
        # validate stock
        for line in cart_items.values():
            p = s.get(Product, line["product_id"])
            if not p:
                raise ValueError(f"Product missing: {line['product_name']}")
            if p.quantity_on_hand < line["quantity"]:
                raise ValueError(
                    f"Insufficient stock for '{p.product_name}' (have {p.quantity_on_hand})."
                )

        subtotal = round(sum(line["line_total"] for line in cart_items.values()), 2)
        total = round(max(subtotal - float(discount_amount), 0.0), 2)

        order = Order(
            customer_id=customer_id,
            staff_id=staff_id,
            subtotal=subtotal,
            discount_amount=float(discount_amount),
            total_amount=total,
            order_type=order_type,
            order_status="Pending",
            payment_method=payment_method,
            payment_status="Paid" if payment_method == "Cash" else "Pending",
            voucher_code=voucher_code,
            delivery_notes=delivery_notes,
        )
        s.add(order)
        s.flush()

        for line in cart_items.values():
            item = OrderItem(
                order_id=order.order_id,
                product_id=line["product_id"],
                product_name=line["product_name"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                subtotal=line["line_total"],
            )
            s.add(item)
            s.flush()
            for opt in line.get("options", []):
                s.add(
                    OrderItemOption(
                        order_item_id=item.order_item_id,
                        option_name=opt["option_name"],
                        additional_price=float(opt.get("additional_price", 0.0)),
                    )
                )
            # adjust stock
            p = s.get(Product, line["product_id"])
            p.quantity_on_hand -= line["quantity"]
            p.quantity_sold += line["quantity"]

        s.add(
            PaymentLog(
                order_id=order.order_id,
                payment_method=payment_method,
                payment_status=order.payment_status,
                amount=total,
                remarks="Order placed",
            )
        )

        # Initial history entry
        _log_history(s, order.order_id, None, "Pending",
                     actor=actor_name, notes="Order placed")

        if promotion_id:
            promotion_service.increment_usage(promotion_id)

        return order.order_id


def list_orders(
    status: Optional[str] = None,
    customer_search: str = "",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    order_type: Optional[str] = None,
) -> list[OrderModel]:
    with session_scope() as s:
        q = s.query(Order)
        if status and status != "All":
            q = q.filter(Order.order_status == status)
        if order_type and order_type != "All":
            q = q.filter(Order.order_type == order_type)
        if date_from:
            q = q.filter(Order.order_date >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            q = q.filter(Order.order_date <= datetime.combine(date_to, datetime.max.time()))
        if customer_search:
            like = f"%{customer_search.strip()}%"
            q = q.join(Customer, Order.customer_id == Customer.customer_id).filter(
                or_(
                    Customer.first_name.ilike(like),
                    Customer.last_name.ilike(like),
                    Customer.email.ilike(like),
                )
            )
        rows = q.order_by(Order.order_date.desc()).all()
        return [_row_to_model(o) for o in rows]


def get_order(order_id: int) -> OrderModel | None:
    with session_scope() as s:
        o = s.get(Order, order_id)
        if not o:
            return None
        history_rows = (
            s.query(OrderStatusHistory)
            .filter(OrderStatusHistory.order_id == order_id)
            .order_by(OrderStatusHistory.created_at.asc(), OrderStatusHistory.history_id.asc())
            .all()
        )
        return _row_to_model(o, history_rows)


def get_order_history(order_id: int) -> list[OrderStatusHistoryEntry]:
    with session_scope() as s:
        rows = (
            s.query(OrderStatusHistory)
            .filter(OrderStatusHistory.order_id == order_id)
            .order_by(OrderStatusHistory.created_at.asc(), OrderStatusHistory.history_id.asc())
            .all()
        )
        return [
            OrderStatusHistoryEntry(
                from_status=r.from_status, to_status=r.to_status,
                changed_by=r.changed_by, notes=r.notes, created_at=r.created_at,
            )
            for r in rows
        ]


def update_order_status(order_id: int, new_status: str,
                        actor_name: str | None = None,
                        notes: str | None = None) -> None:
    if new_status not in ORDER_STATUSES:
        raise ValueError("Invalid status")
    with session_scope() as s:
        o = s.get(Order, order_id)
        if not o:
            raise ValueError("Order not found")
        if o.order_status == new_status:
            return  # no-op
        if new_status not in _ALLOWED_TRANSITIONS.get(o.order_status, set()):
            raise ValueError(
                f"Cannot move order from {o.order_status} to {new_status}."
            )
        prev = o.order_status
        o.order_status = new_status
        # Cash payments are settled at order time; mark non-cash as Paid when completed
        if new_status == "Completed" and o.payment_status == "Pending":
            o.payment_status = "Paid"
            s.add(PaymentLog(
                order_id=o.order_id, payment_method=o.payment_method,
                payment_status="Paid", amount=o.total_amount,
                remarks="Payment settled on completion",
            ))
        _log_history(s, order_id, prev, new_status, actor=actor_name, notes=notes)


def cancel_order(order_id: int, actor_name: str | None = None,
                 reason: str | None = None) -> None:
    with session_scope() as s:
        o = s.get(Order, order_id)
        if not o:
            return
        if o.order_status in ("Completed", "Cancelled"):
            raise ValueError(f"Order already {o.order_status}.")
        prev = o.order_status
        # restore stock
        for it in o.items:
            if it.product_id:
                p = s.get(Product, it.product_id)
                if p:
                    p.quantity_on_hand += it.quantity
                    p.quantity_sold = max(0, p.quantity_sold - it.quantity)
        o.order_status = "Cancelled"
        if o.payment_status == "Paid":
            o.payment_status = "Refunded"
            s.add(PaymentLog(
                order_id=o.order_id, payment_method=o.payment_method,
                payment_status="Refunded", amount=o.total_amount,
                remarks="Refunded on cancellation",
            ))
        _log_history(s, order_id, prev, "Cancelled", actor=actor_name,
                     notes=reason or "Order cancelled")


def mark_email_sent(order_id: int, email: str) -> None:
    with session_scope() as s:
        o = s.get(Order, order_id)
        if o:
            o.email_sent_to = email
            o.email_sent_at = datetime.now()
