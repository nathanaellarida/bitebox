"""SQLAlchemy ORM models for the inventory system."""
from __future__ import annotations

from datetime import datetime, date
from sqlalchemy import (
    Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_description: Mapped[str | None] = mapped_column(Text)
    product_price: Mapped[float] = mapped_column(Float, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.category_id"))
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0)
    quantity_sold: Mapped[int] = mapped_column(Integer, default=0)
    product_image_path: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_by: Mapped[str | None] = mapped_column(String(100))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.now)

    category: Mapped[Category | None] = relationship(back_populates="products")
    option_groups: Mapped[list["ProductOptionGroup"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductOptionGroup(Base):
    __tablename__ = "product_option_groups"

    group_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    group_name: Mapped[str] = mapped_column(String(100))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    max_choices: Mapped[int] = mapped_column(Integer, default=1)

    product: Mapped[Product] = relationship(back_populates="option_groups")
    items: Mapped[list["ProductOptionItem"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class ProductOptionItem(Base):
    __tablename__ = "product_option_items"

    item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("product_option_groups.group_id"))
    option_name: Mapped[str] = mapped_column(String(100))
    additional_price: Mapped[float] = mapped_column(Float, default=0.0)

    group: Mapped[ProductOptionGroup] = relationship(back_populates="items")


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    contact_number: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)
    # Structured delivery address (added later, all nullable to keep
    # existing rows valid). The legacy `address` field still holds any
    # free-form notes the user might have typed.
    street: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    province: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    landmark: Mapped[str | None] = mapped_column(String(200))
    password_hash: Mapped[str | None] = mapped_column(String(255))  # nullable: walk-ins
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Staff(Base):
    __tablename__ = "staff"

    staff_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="Staff")  # Admin or Staff
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Promotion(Base):
    __tablename__ = "promotions"

    promotion_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    promotion_name: Mapped[str] = mapped_column(String(200), nullable=False)
    promotion_description: Mapped[str | None] = mapped_column(Text)
    discount_type: Mapped[str] = mapped_column(String(20))  # Percentage / FixedAmount
    discount_value: Mapped[float] = mapped_column(Float, nullable=False)
    minimum_order_amount: Mapped[float] = mapped_column(Float, default=0.0)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    usage_limit: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PromotionProduct(Base):
    __tablename__ = "promotion_products"

    promotion_id: Mapped[int] = mapped_column(
        ForeignKey("promotions.promotion_id"), primary_key=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id"), primary_key=True
    )


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.customer_id"))
    staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.staff_id"))
    order_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), default="Dine-In")
    order_status: Mapped[str] = mapped_column(String(30), default="Pending")
    payment_method: Mapped[str | None] = mapped_column(String(30))
    payment_status: Mapped[str] = mapped_column(String(20), default="Pending")
    voucher_code: Mapped[str | None] = mapped_column(String(50))
    delivery_notes: Mapped[str | None] = mapped_column(Text)
    email_sent_to: Mapped[str | None] = mapped_column(String(200))
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    customer: Mapped[Customer | None] = relationship()
    staff: Mapped[Staff | None] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.product_id"))
    product_name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    options: Mapped[list["OrderItemOption"]] = relationship(
        back_populates="order_item", cascade="all, delete-orphan"
    )


class OrderItemOption(Base):
    __tablename__ = "order_item_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.order_item_id"))
    option_name: Mapped[str] = mapped_column(String(100))
    additional_price: Mapped[float] = mapped_column(Float, default=0.0)

    order_item: Mapped[OrderItem] = relationship(back_populates="options")


class PaymentLog(Base):
    __tablename__ = "payment_logs"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id"))
    payment_method: Mapped[str | None] = mapped_column(String(30))
    payment_status: Mapped[str | None] = mapped_column(String(20))
    amount: Mapped[float | None] = mapped_column(Float)
    transaction_reference: Mapped[str | None] = mapped_column(String(100))
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class OrderStatusHistory(Base):
    """Audit trail of every status transition on an order."""
    __tablename__ = "order_status_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id"))
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
