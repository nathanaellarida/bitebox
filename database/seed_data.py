"""Insert default admin, sample categories, sample products, and the
forever-on welcome promotions on first run."""
from __future__ import annotations

from datetime import datetime, timedelta

import bcrypt

from database.db_manager import session_scope
from database.models import (
    Category, Customer, Order, OrderItem, OrderStatusHistory, PaymentLog,
    Product, Promotion, Staff,
)


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def run_seed() -> None:
    with session_scope() as s:
        if s.query(Staff).count() == 0:
            s.add(
                Staff(
                    first_name="Admin",
                    last_name="User",
                    email="admin@store.com",
                    password_hash=_hash("Admin@1234"),
                    role="Admin",
                )
            )
            s.add(
                Staff(
                    first_name="Maria",
                    last_name="Santos",
                    email="maria@store.com",
                    password_hash=_hash("Staff@1234"),
                    role="Staff",
                )
            )

        if s.query(Customer).count() == 0:
            s.add_all([
                Customer(
                    first_name="Juan",
                    last_name="Dela Cruz",
                    email="juan@example.com",
                    contact_number="0917-555-1234",
                    address="123 Mango St., Lapu-Lapu City",
                    street="123 Mango St.",
                    city="Lapu-Lapu City",
                    province="Cebu",
                    postal_code="6015",
                    landmark="Near Gaisano Mactan",
                    password_hash=_hash("Customer@1234"),
                    is_active=True,
                ),
                Customer(
                    first_name="Sofia",
                    last_name="Reyes",
                    email="sofia@example.com",
                    contact_number="0918-222-9988",
                    address="45 Pelaez St., Cebu City",
                    street="45 Pelaez St.",
                    city="Cebu City",
                    province="Cebu",
                    postal_code="6000",
                    password_hash=_hash("Customer@1234"),
                    is_active=True,
                ),
            ])

        if s.query(Category).count() == 0:
            categories = [
                Category(category_name="Beverages"),
                Category(category_name="Snacks"),
                Category(category_name="Main Dishes"),
            ]
            s.add_all(categories)
            s.flush()

            cat_map = {c.category_name: c.category_id for c in categories}
            sample_products = [
                Product(
                    product_name="Iced Coffee",
                    product_description="Cold brew with milk",
                    product_price=120.0,
                    category_id=cat_map["Beverages"],
                    quantity_on_hand=50,
                ),
                Product(
                    product_name="Lemonade",
                    product_description="Fresh lemonade",
                    product_price=90.0,
                    category_id=cat_map["Beverages"],
                    quantity_on_hand=40,
                ),
                Product(
                    product_name="Potato Chips",
                    product_description="Salted potato chips",
                    product_price=55.0,
                    category_id=cat_map["Snacks"],
                    quantity_on_hand=100,
                ),
                Product(
                    product_name="Spaghetti",
                    product_description="Filipino-style sweet spaghetti",
                    product_price=180.0,
                    category_id=cat_map["Main Dishes"],
                    quantity_on_hand=25,
                ),
                Product(
                    product_name="Chicken Adobo",
                    product_description="Classic adobo with rice",
                    product_price=220.0,
                    category_id=cat_map["Main Dishes"],
                    quantity_on_hand=20,
                ),
            ]
            s.add_all(sample_products)

        # Forever-on welcome promotions — only seeded on first run
        if s.query(Promotion).count() == 0:
            s.add_all([
                Promotion(
                    promotion_name="10% Welcome Discount",
                    promotion_description="A small thank-you for joining us.",
                    discount_type="Percentage",
                    discount_value=10.0,
                    minimum_order_amount=0.0,
                    code="SAVE10",
                    usage_limit=None,        # unlimited
                    start_date=None,         # no start
                    end_date=None,           # no end → forever
                    is_active=True,
                ),
                Promotion(
                    promotion_name="₱50 Off ₱500+",
                    promotion_description="Flat ₱50 off when your order is at least ₱500.",
                    discount_type="FixedAmount",
                    discount_value=50.0,
                    minimum_order_amount=500.0,
                    code="MABUHAY50",
                    usage_limit=None,
                    start_date=None,
                    end_date=None,
                    is_active=True,
                ),
            ])

        # Sample completed orders so dashboards aren't empty on first run.
        if s.query(Order).count() == 0:
            # Flush so any newly-added staff/customers/products from earlier
            # blocks in this same transaction are queryable below.
            s.flush()
            customers = s.query(Customer).order_by(Customer.customer_id).all()
            staff = s.query(Staff).order_by(Staff.staff_id).all()
            products = {p.product_name: p for p in s.query(Product).all()}
            if customers and staff and products:
                _seed_sample_orders(s, customers, staff, products)


def _seed_sample_orders(s, customers, staff, products) -> None:
    """Generate a handful of realistic past orders with full audit trail."""
    now = datetime.now()
    samples = [
        {
            "customer": customers[0],
            "staff": staff[0],
            "days_ago": 6,
            "items": [("Iced Coffee", 2), ("Spaghetti", 1)],
            "order_type": "Dine-In",
            "payment": "Cash",
            "status": "Completed",
        },
        {
            "customer": customers[1],
            "staff": staff[0],
            "days_ago": 4,
            "items": [("Chicken Adobo", 1), ("Lemonade", 2), ("Potato Chips", 1)],
            "order_type": "Takeout",
            "payment": "GCash",
            "status": "Completed",
        },
        {
            "customer": customers[0],
            "staff": staff[-1],
            "days_ago": 2,
            "items": [("Iced Coffee", 1), ("Potato Chips", 2)],
            "order_type": "Delivery",
            "payment": "Credit Card",
            "status": "Completed",
            "delivery_notes": "Recipient: Juan Dela Cruz\nContact: 0917-555-1234\n"
                              "Address: 123 Mango St., Lapu-Lapu City, Cebu 6015",
        },
        {
            "customer": customers[1],
            "staff": staff[-1],
            "days_ago": 0,
            "items": [("Spaghetti", 1), ("Lemonade", 1)],
            "order_type": "Dine-In",
            "payment": "Cash",
            "status": "Pending",
        },
    ]

    for sample in samples:
        order_date = now - timedelta(days=sample["days_ago"], hours=2)
        line_rows: list[tuple[Product, int]] = []
        for name, qty in sample["items"]:
            product = products.get(name)
            if not product:
                continue
            line_rows.append((product, qty))
        if not line_rows:
            continue

        subtotal = round(
            sum(p.product_price * qty for p, qty in line_rows), 2
        )
        order = Order(
            customer_id=sample["customer"].customer_id,
            staff_id=sample["staff"].staff_id,
            order_date=order_date,
            subtotal=subtotal,
            discount_amount=0.0,
            total_amount=subtotal,
            order_type=sample["order_type"],
            order_status=sample["status"],
            payment_method=sample["payment"],
            payment_status="Paid" if sample["status"] == "Completed" else "Pending",
            delivery_notes=sample.get("delivery_notes", ""),
            created_at=order_date,
        )
        s.add(order)
        s.flush()

        for product, qty in line_rows:
            line_total = round(product.product_price * qty, 2)
            s.add(
                OrderItem(
                    order_id=order.order_id,
                    product_id=product.product_id,
                    product_name=product.product_name,
                    quantity=qty,
                    unit_price=product.product_price,
                    subtotal=line_total,
                )
            )
            # Reflect quantity sold + on-hand changes so dashboards line up.
            product.quantity_sold += qty
            product.quantity_on_hand = max(0, product.quantity_on_hand - qty)

        s.add(
            PaymentLog(
                order_id=order.order_id,
                payment_method=sample["payment"],
                payment_status=order.payment_status,
                amount=order.total_amount,
                remarks="Seeded sample order",
                created_at=order_date,
            )
        )

        # Audit trail mirrors what the order_service would log.
        s.add(
            OrderStatusHistory(
                order_id=order.order_id,
                from_status=None,
                to_status="Pending",
                changed_by=f"{sample['staff'].first_name} {sample['staff'].last_name}",
                notes="Order placed (sample data)",
                created_at=order_date,
            )
        )
        if sample["status"] == "Completed":
            s.add(
                OrderStatusHistory(
                    order_id=order.order_id,
                    from_status="Pending",
                    to_status="Completed",
                    changed_by=f"{sample['staff'].first_name} {sample['staff'].last_name}",
                    notes="Auto-completed in seed data",
                    created_at=order_date + timedelta(hours=1),
                )
            )
