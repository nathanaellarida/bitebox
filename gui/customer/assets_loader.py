"""Helpers for loading customer-portal imagery.

The portal will look for a few specific files under
``inventory_app/assets/images/customer/``. If a file is missing it falls
back to a tinted placeholder so the UI never breaks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap

from config import ASSETS_DIR

CUSTOMER_IMG_DIR = ASSETS_DIR / "images" / "customer"
CUSTOMER_IMG_DIR.mkdir(parents=True, exist_ok=True)


# Map well-known file names to where they're used. Customers can drop their
# own JPG/PNG files into ``assets/images/customer/`` to override the
# placeholders.
KNOWN_FILES: dict[str, str] = {
    "hero_banner.jpg": "Hero banner shown above the menu (recommended 800×260).",
    "category_bakery.png": "Category icon — Bakery (recommended 96×96, transparent).",
    "category_burger.png": "Category icon — Burger (96×96 transparent).",
    "category_beverage.png": "Category icon — Beverage (96×96 transparent).",
    "category_chicken.png": "Category icon — Chicken (96×96 transparent).",
    "category_pizza.png": "Category icon — Pizza (96×96 transparent).",
    "category_seafood.png": "Category icon — Seafood (96×96 transparent).",
    "category_main.png": "Category icon — Main Dish (96×96 transparent).",
    "category_snack.png": "Category icon — Snack (96×96 transparent).",
    "category_default.png": "Fallback category icon (96×96 transparent).",
    "avatar_user.png": "Header user avatar (square; will be circle-cropped).",
}


def customer_image(name: str) -> Optional[QPixmap]:
    """Return a QPixmap for ``name`` if the file exists, else ``None``."""
    path = CUSTOMER_IMG_DIR / name
    if not path.exists():
        return None
    pix = QPixmap(str(path))
    return pix if not pix.isNull() else None


def category_image(category_name: str, size: int = 56) -> QPixmap:
    """Return a category-icon pixmap for the given name."""
    slug = category_name.strip().lower().replace(" ", "_").replace("-", "_")
    candidates = [
        f"category_{slug}.png",
        f"category_{slug}.jpg",
        "category_default.png",
    ]
    for c in candidates:
        pix = customer_image(c)
        if pix is not None:
            return pix.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
    return _placeholder_pixmap(category_name, size)


def product_image(product_name: str, image_path: Optional[str] = None) -> Optional[QPixmap]:
    """Return a QPixmap for a product.

    Resolution order:
      1. ``image_path`` if provided and the file exists (admin-uploaded image).
      2. A file in ``assets/images/customer/`` whose base name matches the
         product name (case-insensitive), tried with several slug variants
         and common image extensions.
      3. ``None`` if nothing matched, so the caller can render its own
         placeholder.
    """
    # 1) Explicit image saved against the product
    if image_path:
        p = Path(image_path)
        if p.exists():
            pix = QPixmap(str(p))
            if not pix.isNull():
                return pix

    if not product_name:
        return None

    # 2) Name-based lookup against the bundled customer assets.
    base = product_name.strip().lower()
    variants = {
        base,                                # "iced coffee"
        base.replace(" ", "_"),              # "iced_coffee"
        base.replace(" ", "-"),              # "iced-coffee"
        base.replace(" ", ""),               # "icedcoffee"
    }
    extensions = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif")
    for stem in variants:
        for ext in extensions:
            candidate = CUSTOMER_IMG_DIR / f"{stem}{ext}"
            if candidate.exists():
                pix = QPixmap(str(candidate))
                if not pix.isNull():
                    return pix
    return None


def hero_image(width: int = 600, height: int = 220) -> Optional[QPixmap]:
    """Return the hero banner pixmap if present, else None."""
    pix = customer_image("hero_banner.jpg") or customer_image("hero_banner.png")
    if pix is None:
        return None
    return pix.scaled(
        width, height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )


def _placeholder_pixmap(label: str, size: int = 56) -> QPixmap:
    """Render a tinted circular placeholder with the first letter of ``label``."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    bg = QColor("#EEF2FF")
    fg = QColor("#1E1B4B")
    painter.setBrush(bg)
    painter.setPen(QPen(fg, 1.5))
    painter.drawRoundedRect(2, 2, size - 4, size - 4, 14, 14)
    painter.setPen(fg)
    font = painter.font()
    font.setBold(True)
    font.setPointSize(int(size * 0.32))
    painter.setFont(font)
    letter = (label or "·").strip()[:1].upper()
    painter.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter, letter)
    painter.end()
    return QPixmap.fromImage(img)


def circle_avatar(name: str, size: int = 36) -> QPixmap:
    """Return a circular avatar — uses ``avatar_user.png`` if present, else
    a coloured initials disc."""
    src = customer_image("avatar_user.png")
    if src is not None:
        scaled = src.scaled(size, size,
                            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                            Qt.TransformationMode.SmoothTransformation)
        return _circle_crop(scaled, size)

    # Initials disc
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#1E1B4B"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(0, 0, size, size)
    p.setPen(QColor("#ffffff"))
    f = p.font(); f.setBold(True); f.setPointSize(int(size * 0.35))
    p.setFont(f)
    initials = "".join(part[:1].upper() for part in name.split()[:2]) or "?"
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, initials)
    p.end()
    return pix


def _circle_crop(src: QPixmap, size: int) -> QPixmap:
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = _circle_path(size)
    p.setClipPath(path)
    # center-crop
    sx = max(0, (src.width() - size) // 2)
    sy = max(0, (src.height() - size) // 2)
    p.drawPixmap(0, 0, src, sx, sy, size, size)
    p.end()
    return out


def _circle_path(size: int):
    from PyQt6.QtGui import QPainterPath
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    return path


def round_pixmap(src: QPixmap, radius: int = 14) -> QPixmap:
    """Return a copy of `src` with rounded corners."""
    if src.isNull():
        return src
    size = src.size()
    out = QPixmap(size)
    out.fill(Qt.GlobalColor.transparent)
    from PyQt6.QtGui import QPainterPath
    path = QPainterPath()
    path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setClipPath(path)
    p.drawPixmap(0, 0, src)
    p.end()
    return out


def required_images_manifest() -> list[tuple[str, str]]:
    """Return the list of ``(filename, description)`` the user can drop in."""
    return list(KNOWN_FILES.items())
