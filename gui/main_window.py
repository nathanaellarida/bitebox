"""Admin main window — redesigned 2025 layout (no top header)."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QStackedWidget, QStatusBar, QVBoxLayout, QWidget
)

from config import load_config
from models.staff import StaffModel


class MainWindow(QMainWindow):
    def __init__(self, current_staff: StaffModel):
        super().__init__()
        self.current_staff = current_staff
        self.cfg = load_config()
        self.setWindowTitle("Inventory Management — Staff Portal")
        self.resize(1320, 840)

        sidebar = self._build_sidebar()

        # Stacked content area
        self.stack = QStackedWidget()
        self._build_pages()

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(sidebar)

        # Content wrapper with padding
        content_wrap = QWidget()
        wrap_layout = QVBoxLayout(content_wrap)
        wrap_layout.setContentsMargins(24, 20, 24, 20)
        wrap_layout.addWidget(self.stack)
        body.addWidget(content_wrap, 1)

        container = QWidget()
        container.setLayout(body)
        self.setCentralWidget(container)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        self._set_active_button(self.btn_dashboard)
        self.stack.setCurrentWidget(self.dashboard_tab)

    # ------------------- sidebar -------------------
    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        store_name = self.cfg.get("store", {}).get("name", "My Store")
        title = QLabel(store_name)
        title.setObjectName("sidebarTitle")
        sub = QLabel("INVENTORY · POS")
        sub.setObjectName("sidebarSubtitle")
        layout.addWidget(title)
        layout.addWidget(sub)

        # New Order has been removed from the admin sidebar — staff/admins
        # now only manage existing orders. Walk-in / pickup orders live in
        # a separate flow that staff trigger from the Orders tab.

        def _add_btn(text: str, key: str) -> QPushButton:
            b = QPushButton(text)
            b.setObjectName("sidebarBtn")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=key: self._navigate(k))
            layout.addWidget(b)
            return b

        self.btn_dashboard = _add_btn("Dashboard", "dashboard")
        self.btn_products = _add_btn("Products", "products")
        self.btn_categories = _add_btn("Categories", "categories")
        self.btn_orders = _add_btn("Orders", "orders")
        self.btn_customers = _add_btn("Customers", "customers")

        self.btn_staff = _add_btn("Staff", "staff")
        self.btn_staff.setVisible(self.current_staff.role == "Admin")

        self.btn_promotions = _add_btn("Promotions", "promotions")
        self.btn_reports = _add_btn("Reports", "reports")
        self.btn_settings = _add_btn("Settings", "settings")

        layout.addStretch(1)

        # User box at bottom
        user_box = QFrame()
        user_box.setObjectName("sidebarUserBox")
        ub = QHBoxLayout(user_box)
        ub.setContentsMargins(10, 10, 10, 10)
        ub.setSpacing(10)

        initials = (self.current_staff.first_name[:1] + self.current_staff.last_name[:1]).upper()
        avatar = QLabel(initials)
        avatar.setObjectName("sidebarAvatar")
        ub.addWidget(avatar)

        name_box = QVBoxLayout()
        name_box.setSpacing(0)
        name_lbl = QLabel(self.current_staff.full_name)
        name_lbl.setObjectName("sidebarUserName")
        role_lbl = QLabel(self.current_staff.role)
        role_lbl.setObjectName("sidebarUserRole")
        name_box.addWidget(name_lbl)
        name_box.addWidget(role_lbl)
        ub.addLayout(name_box, 1)

        logout = QPushButton("Sign Out")
        logout.setObjectName("sidebarLogoutBtn")
        logout.clicked.connect(self._logout)
        ub.addWidget(logout)

        layout.addWidget(user_box)
        return sidebar

    # ------------------- pages -------------------
    def _build_pages(self) -> None:
        from gui.dashboard_tab import DashboardTab
        from gui.products_tab import ProductsTab
        from gui.categories_tab import CategoriesTab
        from gui.orders_tab import OrdersTab
        from gui.customers_tab import CustomersTab
        from gui.staff_tab import StaffTab
        from gui.promotions_tab import PromotionsTab
        from gui.reports_tab import ReportsTab
        from gui.settings_tab import SettingsTab

        self.dashboard_tab = DashboardTab()
        self.products_tab = ProductsTab(self.current_staff)
        self.categories_tab = CategoriesTab(self.current_staff)
        self.orders_tab = OrdersTab(self.current_staff)
        self.customers_tab = CustomersTab(self.current_staff)
        self.staff_tab = StaffTab(self.current_staff)
        self.promotions_tab = PromotionsTab()
        self.reports_tab = ReportsTab()
        self.settings_tab = SettingsTab()

        for w in (
            self.dashboard_tab, self.products_tab, self.categories_tab,
            self.orders_tab, self.customers_tab, self.staff_tab, self.promotions_tab,
            self.reports_tab, self.settings_tab,
        ):
            self.stack.addWidget(w)

        self.settings_tab.theme_changed.connect(self._reload_theme)

    def _navigate(self, key: str) -> None:
        mapping = {
            "dashboard": (self.btn_dashboard, self.dashboard_tab),
            "products": (self.btn_products, self.products_tab),
            "categories": (self.btn_categories, self.categories_tab),
            "orders": (self.btn_orders, self.orders_tab),
            "customers": (self.btn_customers, self.customers_tab),
            "staff": (self.btn_staff, self.staff_tab),
            "promotions": (self.btn_promotions, self.promotions_tab),
            "reports": (self.btn_reports, self.reports_tab),
            "settings": (self.btn_settings, self.settings_tab),
        }
        btn, widget = mapping[key]
        self._set_active_button(btn)
        self.stack.setCurrentWidget(widget)
        if hasattr(widget, "refresh"):
            widget.refresh()

    def _set_active_button(self, active: QPushButton) -> None:
        for b in (
            self.btn_dashboard, self.btn_products, self.btn_categories,
            self.btn_orders, self.btn_customers, self.btn_staff, self.btn_promotions,
            self.btn_reports, self.btn_settings,
        ):
            b.setChecked(b is active)

    def _reload_theme(self) -> None:
        from main import apply_theme
        apply_theme()

    def _logout(self) -> None:
        if QMessageBox.question(self, "Sign Out", "Sign out of this session?") == QMessageBox.StandardButton.Yes:
            self.close()
