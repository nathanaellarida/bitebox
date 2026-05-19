"""Orders management tab — Active / History, view / update / cancel,
with a full status-history timeline in the detail dialog."""
from __future__ import annotations

from datetime import date, timedelta

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMenu, QMessageBox, QPushButton, QScrollArea, QTabWidget, QTextBrowser,
    QVBoxLayout, QWidget
)

from gui.widgets.data_table import DataTable
from models.staff import StaffModel
from services import order_service

STATUS_COLORS = {
    "Pending": QColor("#FEF3C7"),
    "Processing": QColor("#DBEAFE"),
    "ReadyForPickup": QColor("#FFEDD5"),
    "ReadyForDelivery": QColor("#FFEDD5"),
    "Completed": QColor("#D1FAE5"),
    "Cancelled": QColor("#FEE2E2"),
}

ACTIVE_STATUSES = ("Pending", "Processing", "ReadyForPickup", "ReadyForDelivery")
TERMINAL_STATUSES = ("Completed", "Cancelled")


class OrderDetailDialog(QDialog):
    def __init__(self, order, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Order #{order.order_id}")
        self.setMinimumSize(620, 620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        head = QHBoxLayout()
        title = QLabel(f"<h2 style='margin:0'>Order #{order.order_id}</h2>")
        head.addWidget(title)
        head.addStretch(1)
        badge = QLabel(order.order_status)
        badge.setObjectName(_status_badge(order.order_status))
        head.addWidget(badge)
        layout.addLayout(head)

        sub = QLabel(order.order_date.strftime("%A, %B %d, %Y · %H:%M"))
        sub.setStyleSheet("color:#6B7280;")
        layout.addWidget(sub)

        # ---------- Status timeline ----------
        layout.addSpacing(10)
        layout.addWidget(QLabel("<b>Status Timeline</b>"))
        layout.addWidget(_build_history_panel(order))

        # ---------- Items + meta ----------
        layout.addSpacing(8)
        items_html = ""
        for it in order.items:
            opts = ""
            if it.options:
                opts = "<div style='color:#6B7280;font-size:11px'>" + ", ".join(o.option_name for o in it.options) + "</div>"
            items_html += (
                f"<tr><td>{it.product_name}{opts}</td>"
                f"<td style='text-align:center'>{it.quantity}</td>"
                f"<td style='text-align:right'>₱{it.unit_price:,.2f}</td>"
                f"<td style='text-align:right'>₱{it.subtotal:,.2f}</td></tr>"
            )
        browser = QTextBrowser()
        browser.setHtml(f"""
        <p><b>Type:</b> {order.order_type}<br>
        <b>Customer:</b> {order.customer_name or '—'} ({order.customer_email or '—'})<br>
        <b>Processed by:</b> {order.staff_name or '—'}<br>
        <b>Payment:</b> {order.payment_method or '—'} ({order.payment_status})<br>
        <b>Voucher:</b> {order.voucher_code or '—'}<br>
        <b>Email Sent To:</b> {order.email_sent_to or '—'}
        {f' on {order.email_sent_at.strftime("%Y-%m-%d %H:%M")}' if order.email_sent_at else ''}<br>
        <b>Delivery notes:</b> {order.delivery_notes or '—'}</p>
        <table style='width:100%;border-collapse:collapse'>
            <thead><tr style='background:#F9FAFB'>
                <th align='left' style='padding:6px'>Item</th>
                <th>Qty</th><th align='right'>Unit</th><th align='right'>Subtotal</th>
            </tr></thead>
            <tbody>{items_html}</tbody>
        </table>
        <p style='text-align:right;margin-top:14px'>
            Subtotal: <b>₱{order.subtotal:,.2f}</b><br>
            Discount: -₱{order.discount_amount:,.2f}<br>
            <span style='font-size:18px'>Total: <b>₱{order.total_amount:,.2f}</b></span>
        </p>
        """)
        layout.addWidget(browser, 1)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        bot = QHBoxLayout(); bot.addStretch(1); bot.addWidget(close)
        layout.addLayout(bot)


def _status_badge(status: str) -> str:
    return {
        "Pending": "badgePending",
        "Processing": "badgeProcessing",
        "ReadyForPickup": "badgeReady",
        "ReadyForDelivery": "badgeReady",
        "Completed": "badgeCompleted",
        "Cancelled": "badgeCancelled",
    }.get(status, "chipNeutral")


def _build_history_panel(order) -> QFrame:
    """A scrollable vertical timeline of every status transition."""
    frame = QFrame()
    frame.setStyleSheet("QFrame{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;}")
    v = QVBoxLayout(frame)
    v.setContentsMargins(14, 10, 14, 10)
    v.setSpacing(6)

    if not order.history:
        v.addWidget(QLabel("No history recorded."))
        return frame

    for i, h in enumerate(order.history):
        row = QHBoxLayout()
        dot = QLabel("●")
        is_last = i == len(order.history) - 1
        color = "#10B981" if h.to_status == "Completed" else (
            "#EF4444" if h.to_status == "Cancelled" else (
                "#1E1B4B" if is_last else "#9CA3AF"
            )
        )
        dot.setStyleSheet(f"color:{color};font-size:14px;background:transparent;")
        row.addWidget(dot)

        text = f"<b>{h.to_status}</b>"
        if h.from_status:
            text = f"{h.from_status} → <b>{h.to_status}</b>"
        if h.changed_by:
            text += f" <span style='color:#6B7280'>· by {h.changed_by}</span>"
        if h.notes:
            text += f" <span style='color:#9CA3AF'>· {h.notes}</span>"
        lbl = QLabel(text)
        lbl.setStyleSheet("background:transparent;")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        row.addWidget(lbl, 1)

        when = QLabel(h.created_at.strftime("%Y-%m-%d %H:%M"))
        when.setStyleSheet("color:#6B7280;font-size:11px;background:transparent;")
        row.addWidget(when)

        wrap = QWidget()
        wrap.setLayout(row)
        v.addWidget(wrap)
    return frame


class OrdersTab(QWidget):
    HEADERS = [
        "ID", "Customer", "Order Date", "Items", "Total",
        "Type", "Status", "Payment", "Email Sent To",
    ]

    def __init__(self, current_staff: StaffModel, parent=None):
        super().__init__(parent)
        self.current_staff = current_staff
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("<h2 style='margin:0'>Orders</h2>")
        layout.addWidget(title)
        layout.addSpacing(8)

        # Filters
        bar = QHBoxLayout()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All"] + order_service.ORDER_STATUSES)
        self.status_combo.currentTextChanged.connect(self.refresh)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(date.today() - timedelta(days=30))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(date.today())
        self.date_from.dateChanged.connect(self.refresh)
        self.date_to.dateChanged.connect(self.refresh)

        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("Customer name or email…")
        self.cust_search.textChanged.connect(self.refresh)

        bar.addWidget(QLabel("Status"))
        bar.addWidget(self.status_combo)
        bar.addWidget(QLabel("From"))
        bar.addWidget(self.date_from)
        bar.addWidget(QLabel("To"))
        bar.addWidget(self.date_to)
        bar.addWidget(self.cust_search, 1)
        layout.addLayout(bar)

        # Active vs History tabs
        self.tabs = QTabWidget()
        self.active_table = DataTable(self.HEADERS)
        self.history_table = DataTable(self.HEADERS)
        for t in (self.active_table, self.history_table):
            t.cellDoubleClicked.connect(self._view_selected)
        self.tabs.addTab(self.active_table, "Active Orders")
        self.tabs.addTab(self.history_table, "Order History")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs, 1)

        # Counts shown next to the tab labels
        self._active_count = 0
        self._history_count = 0

        action_row = QHBoxLayout()
        view_btn = QPushButton("View Details")
        view_btn.clicked.connect(self._view_selected)
        self.update_btn = QPushButton("Update Status ▾")
        self.update_btn.clicked.connect(self._show_update_menu)
        complete_btn = QPushButton("Mark Completed")
        complete_btn.setObjectName("successBtn")
        complete_btn.clicked.connect(lambda: self._set_status("Completed"))
        cancel_btn = QPushButton("Cancel Order")
        cancel_btn.setObjectName("dangerBtn")
        cancel_btn.clicked.connect(self._cancel)
        action_row.addStretch(1)
        action_row.addWidget(view_btn)
        action_row.addWidget(self.update_btn)
        action_row.addWidget(complete_btn)
        action_row.addWidget(cancel_btn)
        layout.addLayout(action_row)

        self.refresh()

    # ----- data load -----
    def refresh(self) -> None:
        df = self.date_from.date().toPyDate()
        dt = self.date_to.date().toPyDate()
        rows = order_service.list_orders(
            status=self.status_combo.currentText(),
            customer_search=self.cust_search.text(),
            date_from=df, date_to=dt,
        )
        active = [o for o in rows if o.order_status in ACTIVE_STATUSES]
        history = [o for o in rows if o.order_status in TERMINAL_STATUSES]
        self._active_count = len(active)
        self._history_count = len(history)
        self.tabs.setTabText(0, f"Active Orders ({self._active_count})")
        self.tabs.setTabText(1, f"Order History ({self._history_count})")
        self._populate(self.active_table, active)
        self._populate(self.history_table, history)

    def _populate(self, table: DataTable, rows: list) -> None:
        body, colors = [], []
        for o in rows:
            body.append([
                str(o.order_id), o.customer_name or "Walk-in",
                o.order_date.strftime("%Y-%m-%d %H:%M"),
                str(sum(it.quantity for it in o.items)),
                f"₱{o.total_amount:,.2f}",
                o.order_type, o.order_status,
                f"{o.payment_method or '—'}/{o.payment_status}",
                o.email_sent_to or "—",
            ])
            colors.append(STATUS_COLORS.get(o.order_status))
        table.set_rows(body, colors)

    def _on_tab_changed(self, _idx: int) -> None:
        # nothing data-wise needs to change, but disable status update on history rows
        on_active = self.tabs.currentIndex() == 0
        self.update_btn.setEnabled(on_active)

    def _current_table(self) -> DataTable:
        return self.tabs.currentWidget()

    def _selected_id(self) -> int | None:
        t = self._current_table()
        row = t.currentRow()
        if row < 0:
            return None
        return int(t.item(row, 0).text())

    # ----- actions -----
    def _view_selected(self) -> None:
        oid = self._selected_id()
        if oid is None:
            QMessageBox.information(self, "Select", "Select an order first.")
            return
        o = order_service.get_order(oid)
        if not o:
            return
        OrderDetailDialog(o, self).exec()

    def _show_update_menu(self) -> None:
        oid = self._selected_id()
        if oid is None:
            QMessageBox.information(self, "Select", "Select an order first.")
            return
        o = order_service.get_order(oid)
        if not o:
            return
        allowed = order_service.get_allowed_next_statuses(o.order_status)
        if not allowed:
            QMessageBox.information(self, "Status",
                                    f"Order is {o.order_status}; no further changes.")
            return
        menu = QMenu(self)
        for st in allowed:
            if st == "Cancelled":
                continue  # use the dedicated Cancel button
            act = QAction(f"→ {st}", menu)
            act.triggered.connect(lambda _=False, s=st: self._set_status(s))
            menu.addAction(act)
        # show menu under the button
        menu.exec(self.update_btn.mapToGlobal(self.update_btn.rect().bottomLeft()))

    def _set_status(self, new_status: str) -> None:
        oid = self._selected_id()
        if oid is None:
            QMessageBox.information(self, "Select", "Select an order first.")
            return
        try:
            order_service.update_order_status(
                oid, new_status, actor_name=self.current_staff.full_name,
            )
        except ValueError as e:
            QMessageBox.warning(self, "Cannot update", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        # Send a status-update email to the customer (best-effort).
        self._send_status_email(oid, new_status)
        self.refresh()
        self._select_order_in_current_tabs(oid)

    def _send_status_email(self, order_id: int, new_status: str) -> None:
        """Best-effort email on Processing / Ready / Completed / Cancelled."""
        if new_status not in ("Processing", "ReadyForPickup",
                              "ReadyForDelivery", "Completed", "Cancelled"):
            return
        from services import email_service, order_service as os_, customer_service
        order = os_.get_order(order_id)
        if not order or not order.customer_id:
            return
        customer = customer_service.get_customer(order.customer_id)
        if not customer or not customer.email:
            return
        if new_status == "Completed":
            ok, msg = email_service.send_order_completed(order, customer)
        else:
            ok, msg = email_service.send_order_status_update(order, customer, new_status)
        if ok:
            os_.mark_email_sent(order_id, customer.email)

    def _select_order_in_current_tabs(self, oid: int) -> None:
        """Re-select the moved order on whichever tab now contains it."""
        for tab_idx, table in enumerate((self.active_table, self.history_table)):
            for row in range(table.rowCount()):
                if table.item(row, 0) and int(table.item(row, 0).text()) == oid:
                    self.tabs.setCurrentIndex(tab_idx)
                    table.selectRow(row)
                    return

    def _cancel(self) -> None:
        oid = self._selected_id()
        if oid is None:
            QMessageBox.information(self, "Select", "Select an order first.")
            return
        if QMessageBox.question(
            self, "Cancel Order",
            "Cancel this order, restock items, and refund if paid?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            order_service.cancel_order(
                oid, actor_name=self.current_staff.full_name,
                reason="Cancelled by staff",
            )
        except ValueError as e:
            QMessageBox.warning(self, "Cannot cancel", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self._send_status_email(oid, "Cancelled")
        self.refresh()
        self._select_order_in_current_tabs(oid)
