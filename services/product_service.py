"""Product CRUD + inventory operations."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import IMAGES_DIR
from database.db_manager import session_scope
from database.models import (
    Category,
    Product,
    ProductOptionGroup,
    ProductOptionItem,
)
from models.product import OptionGroupModel, OptionItemModel, ProductModel


def _to_model(p: Product) -> ProductModel:
    cat_name = p.category.category_name if p.category else "—"
    groups: list[OptionGroupModel] = []
    for g in p.option_groups:
        groups.append(
            OptionGroupModel(
                group_id=g.group_id,
                product_id=g.product_id,
                group_name=g.group_name,
                is_required=g.is_required,
                max_choices=g.max_choices,
                items=[
                    OptionItemModel(
                        item_id=i.item_id,
                        group_id=i.group_id,
                        option_name=i.option_name,
                        additional_price=i.additional_price,
                    )
                    for i in g.items
                ],
            )
        )
    return ProductModel(
        product_id=p.product_id,
        product_name=p.product_name,
        product_description=p.product_description,
        product_price=p.product_price,
        category_id=p.category_id,
        category_name=cat_name,
        quantity_on_hand=p.quantity_on_hand,
        quantity_sold=p.quantity_sold,
        is_active=p.is_active,
        is_deleted=p.is_deleted,
        product_image_path=p.product_image_path,
        option_groups=groups,
    )


def list_products(
    category_id: Optional[int] = None,
    status: str = "All",  # "Active", "Inactive", "Deleted", "All"
    search: str = "",
) -> list[ProductModel]:
    with session_scope() as s:
        q = s.query(Product)
        if status == "Active":
            q = q.filter(Product.is_active.is_(True), Product.is_deleted.is_(False))
        elif status == "Inactive":
            q = q.filter(Product.is_active.is_(False), Product.is_deleted.is_(False))
        elif status == "Deleted":
            q = q.filter(Product.is_deleted.is_(True))
        else:
            q = q.filter(Product.is_deleted.is_(False))
        if category_id:
            q = q.filter(Product.category_id == category_id)
        if search:
            like = f"%{search.strip()}%"
            q = q.filter(Product.product_name.ilike(like))
        rows = q.order_by(Product.product_name).all()
        return [_to_model(p) for p in rows]


def get_product(product_id: int) -> Optional[ProductModel]:
    with session_scope() as s:
        p = s.get(Product, product_id)
        return _to_model(p) if p else None


def _save_image(src_path: str, product_id: int) -> str:
    src = Path(src_path)
    if not src.exists():
        return ""
    dest_name = f"{product_id}_{src.name}"
    dest = IMAGES_DIR / dest_name
    try:
        shutil.copy2(str(src), str(dest))
    except Exception:
        return ""
    return str(dest)


def add_product(
    name: str,
    price: float,
    category_id: Optional[int],
    description: str = "",
    quantity_on_hand: int = 0,
    image_path: str | None = "",
    option_groups: Optional[list[dict]] = None,
    image_changed: bool = False,  # accepted but ignored on add
) -> int:
    with session_scope() as s:
        p = Product(
            product_name=name.strip(),
            product_description=description,
            product_price=float(price),
            category_id=category_id,
            quantity_on_hand=int(quantity_on_hand),
        )
        s.add(p)
        s.flush()
        if image_path:
            saved = _save_image(image_path, p.product_id)
            if saved:
                p.product_image_path = saved
        if option_groups:
            _replace_option_groups(s, p.product_id, option_groups)
        return p.product_id


def update_product(
    product_id: int,
    name: str,
    price: float,
    category_id: Optional[int],
    description: str = "",
    quantity_on_hand: int = 0,
    image_path: str | None = None,
    option_groups: Optional[list[dict]] = None,
    image_changed: bool = False,
) -> None:
    """If ``image_changed`` is True, ``image_path`` is applied:

      * a non-empty path replaces the current image (copied into assets)
      * an empty string clears the image entirely

    If ``image_changed`` is False the existing image is preserved.
    """
    with session_scope() as s:
        p = s.get(Product, product_id)
        if not p:
            return
        p.product_name = name.strip()
        p.product_description = description
        p.product_price = float(price)
        p.category_id = category_id
        p.quantity_on_hand = int(quantity_on_hand)
        if image_changed:
            if image_path:
                saved = _save_image(image_path, p.product_id)
                if saved:
                    p.product_image_path = saved
            else:
                p.product_image_path = None
        if option_groups is not None:
            _replace_option_groups(s, p.product_id, option_groups)


def _replace_option_groups(session, product_id: int, groups: list[dict]) -> None:
    session.query(ProductOptionItem).filter(
        ProductOptionItem.group_id.in_(
            session.query(ProductOptionGroup.group_id).filter_by(product_id=product_id)
        )
    ).delete(synchronize_session=False)
    session.query(ProductOptionGroup).filter_by(product_id=product_id).delete()
    session.flush()
    for g in groups:
        og = ProductOptionGroup(
            product_id=product_id,
            group_name=g.get("group_name", ""),
            is_required=bool(g.get("is_required", False)),
            max_choices=int(g.get("max_choices", 1)),
        )
        session.add(og)
        session.flush()
        for it in g.get("items", []):
            session.add(
                ProductOptionItem(
                    group_id=og.group_id,
                    option_name=it.get("option_name", ""),
                    additional_price=float(it.get("additional_price", 0.0)),
                )
            )


def toggle_active(product_id: int) -> None:
    with session_scope() as s:
        p = s.get(Product, product_id)
        if p:
            p.is_active = not p.is_active


def soft_delete_product(product_id: int, deleted_by: str = "") -> None:
    with session_scope() as s:
        p = s.get(Product, product_id)
        if p:
            p.is_deleted = True
            p.deleted_by = deleted_by
            p.deleted_at = datetime.now()


def recover_product(product_id: int) -> None:
    with session_scope() as s:
        p = s.get(Product, product_id)
        if p:
            p.is_deleted = False
            p.deleted_by = None
            p.deleted_at = None


def permanent_delete_product(product_id: int) -> None:
    with session_scope() as s:
        p = s.get(Product, product_id)
        if p:
            s.delete(p)
