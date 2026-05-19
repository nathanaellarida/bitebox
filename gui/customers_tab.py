"""Customers tab — read-only listing, with View / Deactivate (Admin) actions.

Customer records are created exclusively through the Customer Portal's
registration flow. Walk-in customers (no portal account) only exist if
created during legacy / future inline order flows.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTextBrowser, QVBoxLayout, QWidget
)

from gui.widgets.data_table import DataTable
from models.staff import StaffModel
from services import customer_service


class CustomerDetailDialog(QDialog):
    def __init__(self, customer, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Customer #{customer.customer_id}")
        self.setMinimumSize(440, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(customer.full_name)
        title.setStyleSheet("font-size:18px;font-weight:700;")
        layout.addWidget(title)

        sub = QLabel(customer.email)
        sub.setStyleSheet("color:#6B7280;")
        layout.addWidget(sub)

        layout.addSpacing(10)

        chip_row = QHBoxLayout()
        portal = QLabel("Portal Account" if customer.has_portal_account else "Walk-in only")
        portal.setObjectName("chipPrimary" if customer.has_portal_account else "chipNeutral")
        active = QLabel("Active" if customer.is_active else "Deactivated")
        active.setObjectName("badgeCompleted" if customer.is_active else "badgeCancelled")
        chip_row.addWidget(portal)
        chip_row.addWidget(active)
        chip_row.addStretch(1)
        layout.addLayout(chip_row)

        layout.addSpacing(10)
        info = QTextBrowser()
        info.setHtml(f"""
            <p><b>Contact:</b> {customer.contact_number or '—'}<br>
            <b>Address:</b> {customer.address or '—'}<br>
            <b>Total Orders:</b> {customer.total_orders}<br>
            <b>Member since:</b> {customer.created_at.strftime('%Y-%m-%d') if customer.created_at else '—'}</p>
        """)
        layout.addWidget(info, 1)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        bot = QHBoxLayout()
        bot.addStretch(1)
        bot.addWidget(close)
        layout.addLayout(bot)


class CustomersTab(QWidget):
    HEADERS = [
        "ID", "Full Name", "Email", "Contact", "Address",
        "Orders", "Account", "Status", "Member Since",
    ]

    def __init__(self, current_staff: StaffModel, parent=None):
        super().__init__(parent)
        self.current_staff = current_staff
        self._is_admin = current_staff.role == "Admin"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("<h2 style='margin:0'>Customers</h2>")
        sub = QLabel("Customer accounts are created via the Customer Portal.")
        sub.setStyleSheet("color:#6B7280;font-size:12px;")
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addSpacing(10)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name or email…")
        self.search.textChanged.connect(self.refresh)
        bar.addWidget(self.search, 1)
        ref = QPushButton("Refresh")
        ref.clicked.connect(self.refresh)
        bar.addWidget(ref)
        layout.addLayout(bar)

        self.table = DataTable(self.HEADERS)
        self.table.cellDoubleClicked.connect(self._view_selected)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        view_btn = QPushButton("View Profile")
        view_btn.clicked.connect(self._view_selected)
        actions.addStretch(1)
        actions.addWidget(view_btn)
        if self._is_admin:
            self.deact_btn = QPushButton("Deactivate")
            self.deact_btn.setObjectName("dangerBtn")
            self.deact_btn.clicked.connect(self._deactivate)
            self.react_btn = QPushButton("Reactivate")
            self.react_btn.clicked.connect(self._reactivate)
            actions.addWidget(self.react_btn)
            actions.addWidget(self.deact_btn)
        layout.addLayout(actions)

        self.refresh()

    def refresh(self) -> None:
        rows = customer_service.list_customers(self.search.text())
        body = []
        for c in rows:
            body.append([
                str(c.customer_id), c.full_name, c.email,
                c.contact_number or "—",
                (c.address or "—")[:60],
                str(c.total_orders),
                "Portal" if c.has_portal_account else "Walk-in",
                "Active" if c.is_active else "Deactivated",
                c.created_at.strftime("%Y-%m-%d") if c.created_at else "—",
            ])
        self.table.set_rows(body)

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())

    def _view_selected(self) -> None:
        cid = self._selected_id()
        if cid is None:
            return
        c = customer_service.get_customer(cid)
        if not c:
            return
        CustomerDetailDialog(c, self).exec()

    def _deactivate(self) -> None:
        cid = self._selected_id()
        if cid is None:
            return
        if QMessageBox.question(
            self, "Confirm",
            "Deactivate this customer? They will no longer be able to sign in to the portal."
        ) == QMessageBox.StandardButton.Yes:
            customer_service.deactivate_customer(cid)
            self.refresh()

    def _reactivate(self) -> None:
        cid = self._selected_id()
        if cid is None:
            return
        customer_service.reactivate_customer(cid)
        self.refresh()
