"""Customer portal main window — FoodMeal-inspired layout."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize, pyqtProperty
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QStackedWidget, QStatusBar, QVBoxLayout,
    QWidget
)

from config import load_config
from gui.customer.assets_loader import circle_avatar
from gui.customer.cart_panel import CartPanel
from gui.customer.menu_tab import MenuTab
from gui.customer.orders_tab import CustomerOrdersTab
from gui.customer.profile_tab import ProfileTab
from gui.widgets.badged_icon_button import BadgedIconButton
from models.customer import CustomerModel


class _CollapsibleSidebar(QFrame):
    """Animated sidebar that slides between expanded and collapsed widths."""
    EXPANDED_WIDTH = 220
    COLLAPSED_WIDTH = 78

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("customerSidebar")
        self.setMinimumWidth(self.EXPANDED_WIDTH)
        self.setMaximumWidth(self.EXPANDED_WIDTH)
        self._expanded = True
        self._anim = QPropertyAnimation(self, b"maximumWidth")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def is_expanded(self) -> bool:
        return self._expanded

    def toggle(self) -> bool:
        target = (self.COLLAPSED_WIDTH if self._expanded
                  else self.EXPANDED_WIDTH)
        self._expanded = not self._expanded
        self.setMinimumWidth(target)
        self._anim.stop()
        self._anim.setStartValue(self.maximumWidth())
        self._anim.setEndValue(target)
        self._anim.start()
        return self._expanded


class CustomerMainWindow(QMainWindow):
    def __init__(self, customer: CustomerModel):
        super().__init__()
        self.customer = customer
        self.cfg = load_config()
        self.setWindowTitle("Customer Portal")
        self.resize(1320, 820)

        # Root container
        root = QWidget()
        root.setObjectName("customerRoot")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        self.sidebar = self._build_sidebar()
        root_layout.addWidget(self.sidebar)

        # Right side: top bar + body
        right_wrap = QVBoxLayout()
        right_wrap.setContentsMargins(20, 18, 20, 18)
        right_wrap.setSpacing(14)

        right_wrap.addWidget(self._build_topbar())

        body = QHBoxLayout()
        body.setSpacing(16)

        # Stacked content area (scrollable per tab if it overflows)
        self.menu_tab = MenuTab()
        self.orders_tab = CustomerOrdersTab(customer)
        self.profile_tab = ProfileTab(customer)
        self.profile_tab.profile_updated.connect(self._on_profile_updated)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._wrap_scroll(self.menu_tab))
        self.stack.addWidget(self._wrap_scroll(self.orders_tab))
        self.stack.addWidget(self._wrap_scroll(self.profile_tab))
        body.addWidget(self.stack, 4)

        # Cart panel
        self.cart_panel = CartPanel(customer)
        self.cart_panel.cart_changed.connect(self._update_cart_badge)
        self.cart_panel.order_completed.connect(self._on_order_completed)
        body.addWidget(self.cart_panel, 0)

        right_wrap.addLayout(body, 1)

        right_container = QWidget()
        right_container.setLayout(right_wrap)
        root_layout.addWidget(right_container, 1)

        self.setCentralWidget(root)

        self.setStatusBar(QStatusBar())
        self.statusBar().setSizeGripEnabled(False)

        # Wire up signals
        self.menu_tab.item_selected.connect(self._on_item_added_to_cart)
        self._set_active_nav(self.btn_menu)
        self._update_cart_badge()

    # ---------- Sidebar ----------
    def _build_sidebar(self) -> _CollapsibleSidebar:
        side = _CollapsibleSidebar()
        v = QVBoxLayout(side)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Header row: dish-plate logo + brand + collapse toggle
        head = QHBoxLayout()
        head.setContentsMargins(14, 14, 12, 6)
        head.setSpacing(8)

        try:
            import qtawesome as qta
            logo = QLabel()
            logo.setPixmap(qta.icon("fa5s.utensils", color="#ffffff").pixmap(20, 20))
            logo.setStyleSheet("background:transparent;")
            logo.setFixedSize(28, 28)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            logo = QLabel("🍽")
            logo.setStyleSheet("background:transparent;color:#fff;font-size:18px;")
            logo.setFixedSize(28, 28)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_lbl = logo
        head.addWidget(logo)

        self.brand_lbl = QLabel(self.cfg.get("store", {}).get("name", "FoodMeal"))
        self.brand_lbl.setObjectName("customerBrand")
        head.addWidget(self.brand_lbl, 1)

        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setObjectName("customerSidebarToggle")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle_sidebar)
        head.addWidget(self.toggle_btn)
        head_wrap = QFrame(); head_wrap.setLayout(head)
        head_wrap.setStyleSheet("background:transparent;")
        v.addWidget(head_wrap)
        v.addSpacing(18)  # gap between brand row and the nav buttons

        # Nav buttons (icon + label). When collapsed we hide labels.
        self.btn_menu = self._make_nav("🍽", "Dashboard", checked=True,
                                       on_click=lambda: self._navigate(0, self.btn_menu))
        self.btn_orders = self._make_nav("📋", "Order History",
                                         on_click=lambda: self._navigate(1, self.btn_orders))
        self.btn_profile = self._make_nav("👤", "Profile",
                                          on_click=lambda: self._navigate(2, self.btn_profile))
        v.addWidget(self.btn_menu)
        v.addWidget(self.btn_orders)
        v.addWidget(self.btn_profile)

        v.addStretch(1)

        # Bottom card — voucher hint, hidden when there are no promos
        self.upgrade_card = QFrame()
        self.upgrade_card.setObjectName("customerUpgradeCard")
        uc = QVBoxLayout(self.upgrade_card)
        uc.setContentsMargins(14, 14, 14, 14)
        self.upgrade_lbl = QLabel("")
        self.upgrade_lbl.setObjectName("customerUpgradeText")
        self.upgrade_lbl.setWordWrap(True)
        uc.addWidget(self.upgrade_lbl)
        v.addWidget(self.upgrade_card)
        self._refresh_promo_hint()

        return side

    def _make_nav(self, icon: str, label: str, checked: bool = False,
                  on_click=None) -> QPushButton:
        btn = QPushButton(f" {icon}   {label}")
        btn.setObjectName("customerNavBtn")
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(44)
        btn.setProperty("icon_text", icon)
        btn.setProperty("full_text", f" {icon}   {label}")
        if on_click:
            btn.clicked.connect(on_click)
        return btn

    def _toggle_sidebar(self) -> None:
        expanded = self.sidebar.toggle()
        # Show / hide labels next to icons
        for btn in (self.btn_menu, self.btn_orders, self.btn_profile):
            if expanded:
                btn.setText(btn.property("full_text"))
            else:
                btn.setText(f" {btn.property('icon_text')} ")
        self.brand_lbl.setVisible(expanded)
        self.logo_lbl.setVisible(expanded)
        # Only show the upgrade card when expanded *and* a promo is available
        if expanded:
            self._refresh_promo_hint()
        else:
            self.upgrade_card.setVisible(False)

    # ---------- Top bar ----------
    def _build_topbar(self) -> QFrame:
        import qtawesome as qta
        bar = QFrame()
        bar.setObjectName("customerTopBar")
        bar.setMinimumHeight(60)
        l = QHBoxLayout(bar)
        l.setContentsMargins(20, 10, 16, 10)
        l.setSpacing(14)

        self.greeting = QLabel(f"Hey, {self.customer.first_name}")
        self.greeting.setObjectName("customerHello")
        l.addWidget(self.greeting)

        self.search = QLineEdit()
        self.search.setObjectName("customerSearch")
        self.search.setPlaceholderText("🔍   What do you want to eat today?")
        self.search.setMinimumHeight(38)
        self.search.textChanged.connect(self._on_search)
        l.addWidget(self.search, 1)

        # Crisp circular icon buttons (no pill bg, larger glyph)
        def _icon_btn(icon_name: str, tooltip: str, color: str = "#1E1B4B",
                      *, badged: bool = False) -> QPushButton:
            btn = BadgedIconButton() if badged else QPushButton()
            btn.setIcon(qta.icon(icon_name, color=color))
            btn.setIconSize(QSize(22, 22))
            btn.setObjectName("customerIconBtn")
            btn.setFixedSize(40, 40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            return btn

        self.cart_btn = _icon_btn("fa5s.shopping-bag", "Cart", badged=True)
        l.addWidget(self.cart_btn)

        self.bell_btn = _icon_btn("fa5s.bell", "Notifications", color="#F59E0B")
        self.bell_btn.clicked.connect(self._open_notifications)
        l.addWidget(self.bell_btn)

        self.signout_btn = _icon_btn("fa5s.sign-out-alt", "Sign out", color="#EF4444")
        self.signout_btn.clicked.connect(self._logout)
        l.addWidget(self.signout_btn)

        # Notification dot (a tiny red badge on the bell when there are unread items)
        self._unread_count = 0

        self.avatar = QLabel()
        self.avatar.setPixmap(circle_avatar(self.customer.full_name, 38))
        self.avatar.setFixedSize(38, 38)
        self.avatar.setStyleSheet("background:transparent;")
        l.addWidget(self.avatar)
        return bar

    # ---------- Body helpers ----------
    def _wrap_scroll(self, w: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        scroll.setWidget(w)
        return scroll

    # ---------- Navigation ----------
    def _navigate(self, idx: int, btn: QPushButton) -> None:
        self.stack.setCurrentIndex(idx)
        self._set_active_nav(btn)
        # The wrapped widget is `scroll.widget()`
        scroll = self.stack.currentWidget()
        inner = scroll.widget() if isinstance(scroll, QScrollArea) else scroll
        if hasattr(inner, "refresh"):
            inner.refresh()

    def _set_active_nav(self, active: QPushButton) -> None:
        for b in (self.btn_menu, self.btn_orders, self.btn_profile):
            b.setChecked(b is active)

    def _on_search(self, _text: str) -> None:
        # Filter the menu tab — pop a search hook on the menu tab
        if hasattr(self.menu_tab, "set_search"):
            self.menu_tab.set_search(_text)

    # ---------- Cart wiring ----------
    def _on_item_added_to_cart(self, product, qty: int, options: list) -> None:
        self.cart_panel.add_item(product, qty, options)
        from gui.widgets.toast import Toast
        Toast.show_message(self, f"Added {product.product_name} to cart",
                           level="success")
        self.statusBar().showMessage(f"Added {product.product_name} to cart.", 3000)

    def _update_cart_badge(self) -> None:
        n = self.cart_panel.item_count()
        self.cart_btn.setToolTip(f"Cart · {n} items" if n else "Cart")
        if hasattr(self.cart_btn, "set_count"):
            self.cart_btn.set_count(n)

    def _on_order_completed(self, order_id: int) -> None:
        from gui.widgets.toast import Toast
        Toast.show_message(self, f"Order #{order_id} placed successfully",
                           level="success", duration_ms=3000)
        self.statusBar().showMessage(f"Order #{order_id} placed successfully.", 6000)
        self._navigate(1, self.btn_orders)
        self.menu_tab.refresh()

    def _on_profile_updated(self, c: CustomerModel) -> None:
        self.customer = c
        self.cart_panel.customer = c
        self.greeting.setText(f"Hey, {c.first_name}")
        self.avatar.setPixmap(circle_avatar(c.full_name, 38))

    def _logout(self) -> None:
        if QMessageBox.question(self, "Sign Out", "Sign out of the customer portal?") \
                == QMessageBox.StandardButton.Yes:
            self.close()

    def _open_notifications(self) -> None:
        from gui.customer.notifications_panel import NotificationsPanel
        panel = NotificationsPanel(self.customer, anchor_widget=self.bell_btn, parent=self)
        panel.exec()

    def _refresh_promo_hint(self) -> None:
        """Show the best currently-active promo code in the sidebar card.
        Hides the card entirely if no promotions are active."""
        from services import promotion_service
        promos = promotion_service.get_active_promotions()
        if not promos:
            self.upgrade_card.setVisible(False)
            return
        # Pick the one with the largest effective discount as the hint.
        promos.sort(
            key=lambda p: (p.discount_value if p.discount_type == "Percentage"
                           else p.discount_value),
            reverse=True,
        )
        p = promos[0]
        if p.discount_type == "Percentage":
            value_text = f"{p.discount_value:g}% off"
        else:
            value_text = f"₱{p.discount_value:,.0f} off"
        if p.minimum_order_amount > 0:
            value_text += f" on orders ₱{p.minimum_order_amount:,.0f}+"
        self.upgrade_lbl.setText(
            f"Use code <b>{p.code}</b> for {value_text}."
        )
        self.upgrade_card.setVisible(True)
