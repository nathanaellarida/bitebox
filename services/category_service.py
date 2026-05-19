"""Category CRUD."""
from __future__ import annotations

from sqlalchemy import func

from database.db_manager import session_scope
from database.models import Category, Product


def list_categories(include_deleted: bool = False) -> list[dict]:
    with session_scope() as s:
        q = s.query(Category)
        if not include_deleted:
            q = q.filter(Category.is_deleted.is_(False))
        rows = q.order_by(Category.category_name).all()
        result = []
        for c in rows:
            count = (
                s.query(func.count(Product.product_id))
                .filter(Product.category_id == c.category_id, Product.is_deleted.is_(False))
                .scalar()
            )
            result.append(
                {
                    "category_id": c.category_id,
                    "category_name": c.category_name,
                    "is_deleted": c.is_deleted,
                    "product_count": int(count or 0),
                }
            )
        return result


def add_category(name: str) -> int:
    with session_scope() as s:
        c = Category(category_name=name.strip())
        s.add(c)
        s.flush()
        return c.category_id


def update_category(category_id: int, name: str) -> None:
    with session_scope() as s:
        c = s.get(Category, category_id)
        if c:
            c.category_name = name.strip()


def soft_delete_category(category_id: int) -> None:
    with session_scope() as s:
        c = s.get(Category, category_id)
        if c:
            c.is_deleted = True


def recover_category(category_id: int) -> None:
    with session_scope() as s:
        c = s.get(Category, category_id)
        if c:
            c.is_deleted = False


def permanent_delete_category(category_id: int) -> None:
    """Hard-delete a category. Refuses if any product still references it."""
    with session_scope() as s:
        c = s.get(Category, category_id)
        if not c:
            return
        in_use = (
            s.query(func.count(Product.product_id))
            .filter(Product.category_id == category_id)
            .scalar()
        )
        if int(in_use or 0) > 0:
            raise ValueError(
                f"{int(in_use)} product(s) still reference '{c.category_name}'. "
                "Reassign or delete those products first."
            )
        s.delete(c)
