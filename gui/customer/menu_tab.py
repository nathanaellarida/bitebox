"""Customer menu tab — FoodMeal-inspired layout with hero, categories,
and a Popular Dishes grid."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup, QCheckBox, QDialog, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QRadioButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget
)

from gui.customer.assets_loader import (
    category_image, customer_image, hero_image, product_image, round_pixmap,
)
from models.product import ProductModel
from services import category_service, product_service


# ---------------- Reusable cards ----------------

class HeroBanner(QFrame):
    """Full-bleed hero with image background and a left→right dark gradient
    so the title text stays legible regardless of the image."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("customerHero")
        self.setFixedHeight(180)
        self._pixmap = None
        self._radius = 18
        self._reload_image()

    def _reload_image(self) -> None:
        from gui.customer.assets_loader import customer_image
        # Try common filenames, full-bleed images preferred
        for name in ("hero_banner.jpg", "hero_banner.png", "hero.jpg", "hero.png"):
            pix = customer_image(name)
            if pix is not None:
                self._pixmap = pix
                return
        self._pixmap = None

    def paintEvent(self, event):  # noqa
        from PyQt6.QtCore import QPointF, QRectF
        from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())

        # Round-clip the whole frame
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)
        painter.setClipPath(path)

        # 1) Background: image (cover) or solid brand color fallback
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Center crop
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
        else:
            painter.fillRect(self.rect(), QColor("#1E1B4B"))

        # 2) Dark gradient overlay (denser on the left where the text sits)
        grad = QLinearGradient(QPointF(0, 0), QPointF(self.width(), 0))
        grad.setColorAt(0.0, QColor(15, 12, 40, 235))     # very dark on left
        grad.setColorAt(0.55, QColor(15, 12, 40, 110))    # softening to the right
        grad.setColorAt(1.0, QColor(15, 12, 40, 60))      # subtle on the far right
        painter.fillRect(self.rect(), QBrush(grad))

        # 3) A subtle bottom-left vignette to darken the headline strip
        vert = QLinearGradient(QPointF(0, self.height()), QPointF(0, 0))
        vert.setColorAt(0.0, QColor(0, 0, 0, 80))
        vert.setColorAt(0.6, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), QBrush(vert))


def build_hero_banner() -> QFrame:
    """Construct the hero with overlaid text content."""
    hero = HeroBanner()
    layout = QHBoxLayout(hero)
    layout.setContentsMargins(34, 28, 34, 28)

    text_box = QVBoxLayout()
    title = QLabel("Welcome to our menu")
    title.setObjectName("customerHeroTitle")
    title.setWordWrap(True)
    sub = QLabel("Browse our chef's picks and order in a few taps.")
    sub.setObjectName("customerHeroSub")
    sub.setWordWrap(True)
    text_box.addStretch(1)
    text_box.addWidget(title)
    text_box.addWidget(sub)
    text_box.addStretch(1)
    layout.addLayout(text_box, 1)
    layout.addStretch(1)  # let the right side breathe; image fills behind
    return hero


class CategoryCard(QFrame):
    """Horizontal pill: icon + label. Toggleable.

    The icon comes from a small built-in emoji map by category name,
    or a `category_<slug>.png` file dropped in
    ``assets/images/customer/`` if the user wants a custom glyph.
    """
    clicked = pyqtSignal(object)  # category_id (int|None)

    # Lightweight glyph fallback so we don't need PNG files for everyday
    # categories. Custom PNGs (when present) still take precedence.
    _GLYPH_MAP = {
        "all": "✦",
        "signature": "✦",
        "bakery": "🥐",
        "croissant": "🥐",
        "burger": "🍔",
        "burgers": "🍔",
        "pizza": "🍕",
        "pizzas": "🍕",
        "beverage": "🥤",
        "beverages": "🥤",
        "drinks": "🥤",
        "coffee": "☕",
        "tea": "🍵",
        "chicken": "🍗",
        "seafood": "🦐",
        "main dishes": "🍛",
        "main": "🍛",
        "snacks": "🍿",
        "snack": "🍿",
        "dessert": "🍰",
        "desserts": "🍰",
        "ice cream": "🍨",
        "waffle": "🧇",
        "waffles": "🧇",
        "salad": "🥗",
        "noodles": "🍜",
    }

    def __init__(self, category_id, name: str, parent=None):
        super().__init__(parent)
        self.category_id = category_id
        self.setObjectName("categoryCard")
        self.setFixedHeight(46)
        self.setProperty("selected", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        h = QHBoxLayout(self)
        h.setContentsMargins(16, 4, 18, 4)
        h.setSpacing(10)

        # Prefer a user-supplied PNG; otherwise use the emoji glyph.
        icon = QLabel()
        icon.setObjectName("categoryIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(24, 24)
        from gui.customer.assets_loader import customer_image
        slug = name.strip().lower().replace(" ", "_").replace("-", "_")
        pix = customer_image(f"category_{slug}.png") or customer_image(f"category_{slug}.jpg")
        if pix is not None and not pix.isNull():
            icon.setPixmap(pix.scaled(
                22, 22,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        else:
            glyph = self._GLYPH_MAP.get(name.strip().lower(), "•")
            icon.setText(glyph)
        h.addWidget(icon)

        lbl = QLabel(name)
        lbl.setObjectName("categoryName")
        lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        h.addWidget(lbl, 1)

    _SELECTED_QSS = (
        "QFrame#categoryCard{background:#1E1B4B;border:1px solid #1E1B4B;"
        "border-radius:999px;}"
    )
    _UNSELECTED_QSS = (
        "QFrame#categoryCard{background:#ffffff;border:1px solid #F1F5F9;"
        "border-radius:999px;}"
    )

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        # Apply the frame's bg/border directly. Qt's QSS engine doesn't
        # always re-resolve [selected="..."] descendant rules when an
        # ancestor's dynamic property changes, so we drive both the
        # frame and child labels here for a guaranteed refresh.
        self.setStyleSheet(self._SELECTED_QSS if selected else self._UNSELECTED_QSS)
        from PyQt6.QtWidgets import QLabel
        for lbl in self.findChildren(QLabel):
            if lbl.objectName() == "categoryName":
                lbl.setStyleSheet(
                    "background:transparent;font-weight:600;font-size:13px;"
                    "padding-left:4px;padding-right:8px;"
                    f"color:{'#ffffff' if selected else '#111827'};"
                )
            elif lbl.objectName() == "categoryIcon":
                lbl.setStyleSheet(
                    "background:transparent;font-size:18px;"
                    "padding-left:4px;padding-right:4px;"
                    f"color:{'#ffffff' if selected else '#1E1B4B'};"
                )

    def mousePressEvent(self, _event) -> None:  # noqa
        self.clicked.emit(self.category_id)


class DishCard(QFrame):
    """Compact card with image, name, price, and an Add (+) button."""
    add_clicked = pyqtSignal(int)  # product_id

    CARD_WIDTH = 200
    CARD_HEIGHT = 250
    IMG_WIDTH = 176
    IMG_HEIGHT = 124

    def __init__(self, product: ProductModel, parent=None):
        super().__init__(parent)
        self.product = product
        self.setObjectName("dishCard")
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)

        v = QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(6)

        # Image with strong rounded corners
        img_label = QLabel()
        img_label.setFixedSize(self.IMG_WIDTH, self.IMG_HEIGHT)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setStyleSheet(
            "background:#F3F4F6;border-radius:18px;font-size:30px;color:#9CA3AF;"
        )
        if product.product_image_path and Path(product.product_image_path).exists():
            pix = QPixmap(product.product_image_path)
        else:
            pix = product_image(product.product_name, product.product_image_path)
        if pix is not None and not pix.isNull():
            pix = pix.scaled(
                self.IMG_WIDTH, self.IMG_HEIGHT,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            pix = round_pixmap(pix, 18)
            img_label.setPixmap(pix)
        else:
            img_label.setText("🍽")
        v.addWidget(img_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Food name (sits directly under the image — no stretch above)
        name = QLabel(product.product_name)
        name.setObjectName("dishName")
        name.setWordWrap(True)
        name.setMaximumHeight(40)
        v.addWidget(name)

        # Price + Add button immediately below the name
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        price = QLabel(f"₱{product.product_price:,.2f}")
        price.setObjectName("dishPrice")
        bottom.addWidget(price)
        bottom.addStretch(1)

        add = QPushButton("+")
        add.setObjectName("dishAddBtn")
        add.setEnabled(product.quantity_on_hand > 0)
        add.clicked.connect(lambda: self.add_clicked.emit(product.product_id))
        bottom.addWidget(add)
        v.addLayout(bottom)

        if product.quantity_on_hand <= 0:
            sold = QLabel("Out of stock")
            sold.setStyleSheet("color:#EF4444;font-size:11px;background:transparent;")
            v.addWidget(sold)


# ---------------- Options dialog ----------------

class OptionsDialog(QDialog):
    def __init__(self, product: ProductModel, parent=None):
        super().__init__(parent)
        self.setWindowTitle(product.product_name)
        self.setMinimumWidth(420)
        self.product = product
        self.selected: list[dict] = []

        layout = QVBoxLayout(self)

        header = QLabel(f"<h3 style='margin:0'>{product.product_name}</h3>")
        layout.addWidget(header)
        self.price_lbl = QLabel(f"₱{product.product_price:,.2f}")
        self.price_lbl.setStyleSheet("color:#1E1B4B;font-size:18px;font-weight:700;")
        layout.addWidget(self.price_lbl)
        layout.addSpacing(6)

        self._group_widgets: list[tuple] = []
        for grp in product.option_groups:
            box = QGroupBox(f"{grp.group_name}{' *' if grp.is_required else ''}")
            box.setStyleSheet("QGroupBox{font-weight:600;}")
            v = QVBoxLayout(box)
            ctrls: list = []
            metas: list[dict] = []
            if grp.max_choices == 1:
                bg = QButtonGroup(box)
                for i, item in enumerate(grp.items):
                    rb = QRadioButton(f"{item.option_name}  (+₱{item.additional_price:.2f})")
                    if i == 0 and grp.is_required:
                        rb.setChecked(True)
                    rb.toggled.connect(self._update_total)
                    bg.addButton(rb)
                    v.addWidget(rb)
                    ctrls.append(rb)
                    metas.append({"option_name": item.option_name, "additional_price": item.additional_price})
            else:
                for item in grp.items:
                    cb = QCheckBox(f"{item.option_name}  (+₱{item.additional_price:.2f})")
                    cb.toggled.connect(self._update_total)
                    v.addWidget(cb)
                    ctrls.append(cb)
                    metas.append({"option_name": item.option_name, "additional_price": item.additional_price})
            layout.addWidget(box)
            self._group_widgets.append((grp, ctrls, metas))

        qty_row = QHBoxLayout()
        qty_row.addWidget(QLabel("Quantity"))
        self.qty = QSpinBox()
        self.qty.setRange(1, max(1, product.quantity_on_hand))
        self.qty.valueChanged.connect(self._update_total)
        qty_row.addWidget(self.qty)
        qty_row.addStretch(1)
        layout.addLayout(qty_row)

        self.total_lbl = QLabel("")
        self.total_lbl.setStyleSheet("font-size:16px;font-weight:700;")
        self.total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.total_lbl)
        self._update_total()

        btns = QHBoxLayout()
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        ok = QPushButton("Add to Cart"); ok.setObjectName("primaryBtn"); ok.clicked.connect(self._confirm)
        btns.addStretch(1); btns.addWidget(cancel); btns.addWidget(ok)
        layout.addLayout(btns)

    def _current_extra(self) -> tuple[float, list[dict]]:
        extra = 0.0
        chosen: list[dict] = []
        for grp, ctrls, metas in self._group_widgets:
            for c, m in zip(ctrls, metas):
                if c.isChecked():
                    extra += m["additional_price"]
                    chosen.append(m)
        return extra, chosen

    def _update_total(self) -> None:
        extra, _ = self._current_extra()
        unit = self.product.product_price + extra
        total = unit * self.qty.value()
        self.total_lbl.setText(f"Total: ₱{total:,.2f}")

    def _confirm(self) -> None:
        chosen: list[dict] = []
        for grp, ctrls, metas in self._group_widgets:
            picked = [m for c, m in zip(ctrls, metas) if c.isChecked()]
            if grp.is_required and not picked:
                self.total_lbl.setText(f"Please choose an option for {grp.group_name}")
                self.total_lbl.setStyleSheet("color:#EF4444;font-weight:600;")
                return
            if len(picked) > grp.max_choices:
                self.total_lbl.setText(f"Pick at most {grp.max_choices} for {grp.group_name}")
                self.total_lbl.setStyleSheet("color:#EF4444;font-weight:600;")
                return
            chosen.extend(picked)
        self.selected = chosen
        self.accept()


# ---------------- Menu tab ----------------

class MenuTab(QWidget):
    """The customer dashboard: hero banner, categories, popular dishes."""
    item_selected = pyqtSignal(object, int, list)  # (ProductModel, qty, options)

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)

        # Hero promo banner
        v.addWidget(self._build_hero())

        # Category section
        v.addWidget(self._build_section_header("Category"))
        self._cat_layout = QHBoxLayout()
        self._cat_layout.setSpacing(14)
        self._cat_layout.setContentsMargins(2, 0, 2, 0)
        cat_wrap = QFrame(); cat_wrap.setLayout(self._cat_layout)
        cat_wrap.setStyleSheet("background:transparent;")
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(64)
        cat_scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cat_scroll.setWidget(cat_wrap)
        v.addWidget(cat_scroll)

        # Popular dishes section
        v.addWidget(self._build_section_header("Popular Dishes"))
        from gui.customer.flow_layout import FlowLayout
        self.dishes_layout = FlowLayout(hspacing=14, vspacing=14)
        self.dishes_layout.setContentsMargins(0, 0, 0, 0)
        dishes_wrap = QWidget()
        dishes_wrap.setLayout(self.dishes_layout)
        dishes_scroll = QScrollArea()
        dishes_scroll.setWidgetResizable(True)
        dishes_scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        dishes_scroll.setWidget(dishes_wrap)
        v.addWidget(dishes_scroll, 1)

        self._cat_id: int | None = None
        self._cat_cards: list[CategoryCard] = []
        self._search: str = ""

        # Populate immediately so the dashboard is not blank on first show.
        self.refresh()

    # -------- helpers --------
    def _build_hero(self) -> QFrame:
        return build_hero_banner()

    def _build_section_header(self, title: str) -> QWidget:
        w = QFrame()
        w.setStyleSheet("background:transparent;")
        l = QHBoxLayout(w)
        l.setContentsMargins(2, 0, 2, 0)
        lbl = QLabel(title)
        lbl.setObjectName("customerSection")
        l.addWidget(lbl)
        l.addStretch(1)
        view_all = QPushButton("View all  ›")
        view_all.setObjectName("customerViewAll")
        l.addWidget(view_all)
        return w

    def _scroll_to_dishes(self) -> None:
        # The cards section is far enough below the hero that this is a
        # purely cosmetic click; the dish grid is already visible.
        pass

    # -------- public --------
    def set_search(self, text: str) -> None:
        self._search = text or ""
        self._refresh_dishes()

    def refresh(self) -> None:
        self._refresh_categories()
        self._refresh_dishes()

    def _refresh_categories(self) -> None:
        # clear
        while self._cat_layout.count():
            it = self._cat_layout.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
        self._cat_cards.clear()

        cats = [{"id": None, "name": "All"}] + [
            {"id": c["category_id"], "name": c["category_name"]}
            for c in category_service.list_categories()
        ]
        for c in cats:
            card = CategoryCard(c["id"], c["name"])
            card.clicked.connect(self._on_category_picked)
            if c["id"] == self._cat_id:
                card.set_selected(True)
            self._cat_layout.addWidget(card)
            self._cat_cards.append(card)
        self._cat_layout.addStretch(1)

    def _on_category_picked(self, cat_id) -> None:
        self._cat_id = cat_id
        for card in self._cat_cards:
            card.set_selected(card.category_id == cat_id)
        self._refresh_dishes()

    def _refresh_dishes(self) -> None:
        # FlowLayout.takeAt + setParent(None) clears existing cards.
        while self.dishes_layout.count():
            it = self.dishes_layout.takeAt(0)
            if it is not None and it.widget() is not None:
                it.widget().setParent(None)
        products = product_service.list_products(
            category_id=self._cat_id, status="Active", search=self._search,
        )
        for p in products:
            card = DishCard(p)
            card.add_clicked.connect(self._on_add)
            self.dishes_layout.addWidget(card)

    def _on_add(self, product_id: int) -> None:
        """Quick-add: clicking the + button adds one unit with no options
        and no modal. Customers can adjust quantity from the cart panel."""
        p = product_service.get_product(product_id)
        if not p or p.quantity_on_hand <= 0:
            return
        self.item_selected.emit(p, 1, [])
