"""Reports: products, orders, dashboard. CSV / PDF export."""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import func, or_

from database.db_manager import session_scope
from database.models import Category, Customer, Order, OrderItem, Product

# ----------------------- Products report -----------------------

def products_report(
    category_id: Optional[int] = None,
    status: str = "All",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    with session_scope() as s:
        q = s.query(Product)
        if status == "Active":
            q = q.filter(Product.is_active.is_(True), Product.is_deleted.is_(False))
        elif status == "Inactive":
            q = q.filter(Product.is_active.is_(False), Product.is_deleted.is_(False))
        else:
            q = q.filter(Product.is_deleted.is_(False))
        if category_id:
            q = q.filter(Product.category_id == category_id)
        rows = q.all()
        result = []
        for p in rows:
            qty_sold = p.quantity_sold
            # When date filters applied, override qty_sold with the period sum
            if date_from or date_to:
                iq = s.query(func.coalesce(func.sum(OrderItem.quantity), 0)).join(
                    Order, Order.order_id == OrderItem.order_id
                ).filter(OrderItem.product_id == p.product_id)
                if date_from:
                    iq = iq.filter(Order.order_date >= datetime.combine(date_from, datetime.min.time()))
                if date_to:
                    iq = iq.filter(Order.order_date <= datetime.combine(date_to, datetime.max.time()))
                qty_sold = int(iq.scalar() or 0)

            result.append(
                {
                    "product_id": p.product_id,
                    "product_name": p.product_name,
                    "category": p.category.category_name if p.category else "—",
                    "price": round(p.product_price, 2),
                    "quantity_on_hand": p.quantity_on_hand,
                    "quantity_sold": qty_sold,
                    "revenue": round(qty_sold * p.product_price, 2),
                    "status": "Active" if p.is_active else "Inactive",
                }
            )
        return result


# ----------------------- Orders report -----------------------

def orders_report(
    status: str = "All",
    customer_search: str = "",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    order_type: str = "All",
) -> list[dict]:
    with session_scope() as s:
        q = s.query(Order)
        if status != "All":
            q = q.filter(Order.order_status == status)
        if order_type != "All":
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
        result = []
        for o in rows:
            customer_name = (
                f"{o.customer.first_name} {o.customer.last_name}"
                if o.customer else "—"
            )
            customer_email = o.customer.email if o.customer else "—"
            staff_name = (
                f"{o.staff.first_name} {o.staff.last_name}" if o.staff else "—"
            )
            items_summary = ", ".join(f"{it.product_name} x{it.quantity}" for it in o.items)
            result.append(
                {
                    "order_id": o.order_id,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "order_date": o.order_date.strftime("%Y-%m-%d %H:%M"),
                    "items": items_summary,
                    "subtotal": round(o.subtotal, 2),
                    "discount": round(o.discount_amount, 2),
                    "total": round(o.total_amount, 2),
                    "order_type": o.order_type,
                    "status": o.order_status,
                    "payment_method": o.payment_method or "—",
                    "email_sent_to": o.email_sent_to or "—",
                    "email_sent_at": o.email_sent_at.strftime("%Y-%m-%d %H:%M") if o.email_sent_at else "—",
                    "processed_by": staff_name,
                }
            )
        return result


# ----------------------- Dashboard -----------------------

def dashboard_stats(period: str = "today") -> dict:
    """period: 'today' | 'month' | 'year'"""
    now = datetime.now()
    if period == "today":
        start = datetime.combine(now.date(), datetime.min.time())
    elif period == "month":
        start = datetime(now.year, now.month, 1)
    elif period == "year":
        start = datetime(now.year, 1, 1)
    else:
        start = datetime.combine(now.date(), datetime.min.time())

    with session_scope() as s:
        period_orders_q = s.query(Order).filter(Order.order_date >= start)
        period_orders = period_orders_q.count()
        period_revenue = float(
            period_orders_q.with_entities(func.coalesce(func.sum(Order.total_amount), 0.0))
            .filter(Order.order_status != "Cancelled").scalar() or 0.0
        )
        total_orders = s.query(Order).count()
        total_revenue = float(
            s.query(func.coalesce(func.sum(Order.total_amount), 0.0))
            .filter(Order.order_status != "Cancelled").scalar() or 0.0
        )
        total_customers = s.query(Customer).count()
        avg_order_value = (total_revenue / total_orders) if total_orders else 0.0

        # best sellers by qty sold
        best = (
            s.query(Product.product_name, Product.quantity_sold,
                    (Product.quantity_sold * Product.product_price).label("rev"))
            .order_by(Product.quantity_sold.desc())
            .limit(5)
            .all()
        )
        best_sellers = [
            {"product_name": r[0], "quantity_sold": int(r[1] or 0), "revenue": float(r[2] or 0.0)}
            for r in best
        ]

        # status distribution
        status_rows = (
            s.query(Order.order_status, func.count(Order.order_id))
            .group_by(Order.order_status).all()
        )
        status_distribution = {row[0]: int(row[1]) for row in status_rows}

        # last 7 days revenue trend
        trend = []
        for i in range(6, -1, -1):
            d_start = datetime.combine((now - timedelta(days=i)).date(), datetime.min.time())
            d_end = d_start + timedelta(days=1)
            rev = float(
                s.query(func.coalesce(func.sum(Order.total_amount), 0.0))
                .filter(Order.order_date >= d_start, Order.order_date < d_end,
                        Order.order_status != "Cancelled")
                .scalar() or 0.0
            )
            trend.append({"date": d_start.strftime("%m/%d"), "revenue": rev})

        recent = (
            s.query(Order).order_by(Order.order_date.desc()).limit(10).all()
        )
        recent_orders = []
        for o in recent:
            cn = f"{o.customer.first_name} {o.customer.last_name}" if o.customer else "—"
            recent_orders.append(
                {
                    "order_id": o.order_id,
                    "customer_name": cn,
                    "total": round(o.total_amount, 2),
                    "status": o.order_status,
                    "order_date": o.order_date.strftime("%Y-%m-%d %H:%M"),
                }
            )

        return {
            "period": period,
            "period_orders": period_orders,
            "period_revenue": round(period_revenue, 2),
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "total_customers": total_customers,
            "avg_order_value": round(avg_order_value, 2),
            "best_sellers": best_sellers,
            "status_distribution": status_distribution,
            "trend": trend,
            "recent_orders": recent_orders,
        }


# ----------------------- Exports -----------------------

def export_csv(data: list[dict], filepath: str) -> None:
    if not data:
        Path(filepath).write_text("(no data)", encoding="utf-8")
        return
    fieldnames = list(data[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def export_pdf(
    data: list[dict],
    filepath: str,
    title: str,
    store_name: str = "Store",
    summary: dict | None = None,
) -> None:
    """PDF generation via reportlab. Raises on failure."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    )

    doc = SimpleDocTemplate(filepath, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"<b>{store_name}</b>", styles["Title"]),
        Paragraph(title, styles["Heading2"]),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]),
        Spacer(1, 12),
    ]
    if summary:
        rows = [[k, str(v)] for k, v in summary.items()]
        t = Table([["Summary", ""]] + rows, colWidths=[180, 200])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A56DB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))
    if not data:
        story.append(Paragraph("No data.", styles["Normal"]))
    else:
        headers = list(data[0].keys())
        body = [headers] + [[str(row.get(h, "")) for h in headers] for row in data]
        t = Table(body, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A56DB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FB")]),
        ]))
        story.append(t)
    doc.build(story)
