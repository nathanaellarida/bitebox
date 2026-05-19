from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class OptionItemModel:
    item_id: int
    group_id: int
    option_name: str
    additional_price: float = 0.0


@dataclass
class OptionGroupModel:
    group_id: int
    product_id: int
    group_name: str
    is_required: bool = False
    max_choices: int = 1
    items: list[OptionItemModel] = field(default_factory=list)


@dataclass
class ProductModel:
    product_id: int
    product_name: str
    product_price: float
    category_id: int | None
    category_name: str
    quantity_on_hand: int
    quantity_sold: int
    is_active: bool
    is_deleted: bool
    product_image_path: str | None = None
    product_description: str | None = None
    option_groups: list[OptionGroupModel] = field(default_factory=list)
