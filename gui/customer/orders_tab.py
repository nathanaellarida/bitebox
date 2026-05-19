"""Customer 'My Orders' tab — card list, scoped to logged-in customer."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QTextBrowser, QVBoxLayout, QWidget
)

from models.customer import CustomerModel
from services import order_service

_STATUS_BADGE = {
    "Pending": "badgePending",
    "Processing": "badgeProcessing",
    "ReadyForPickup": "badgeReady",
    "ReadyForDelivery": "badgeReady",
    "Completed": "badgeCompleted",
    "Cancelled": "badgeCancelled",
}
_STATUS_FLOW = ["Pending", "Processing", "ReadyForPickup", "Completed"]


class OrderDetailDialog(QDialog):
    def __init__(self, order, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Order #{order.order_id}")
        self.setMinimumSize(560, 580)

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 20)

        head = QHBoxLayout()
        title = QLabel(f"<h3 style='margin:0'>Order #{order.order_id}</h3>")
        head.addWidget(title)
        head.addStretch(1)
        badge = QLabel(order.order_status)
        badge.setObjectName(_STATUS_BADGE.get(order.order_status, "chipNeutral"))
        head.addWidget(badge)
        v.addLayout(head)

        sub = QLabel(order.order_date.strftime("%A, %B %d, %Y · %H:%M"))
        sub.setStyleSheet("color:#6B7280;")
        v.addWidget(sub)

        # Status timeline (stepper)
        v.addSpacing(10)
        v.addWidget(self._build_timeline(order))

        v.addSpacing(8)
        # Items
        items_html = ""
        for it in order.items:
            opt = ""
            if it.options:
                opt = "<div style='color:#6B7280;font-size:11px'>" + ", ".join(o.option_name for o in it.options) + "</div>"
            items_html += (
                f"<tr>"
                f"<td>{it.product_name}{opt}</td>"
                f"<td style='text-align:center'>{it.quantity}</td>"
                f"<td style='text-align:right'>₱{it.unit_price:,.2f}</td>"
                f"<td style='text-align:right'>₱{it.subtotal:,.2f}</td>"
                f"</tr>"
            )
        browser = QTextBrowser()
        browser.setHtml(f"""
            <table style='width:100%;border-collapse:collapse'>
                <thead><tr style='background:#F9FAFB'>
                    <th align='left' style='padding:6px'>Item</th>
                    <th>Qty</th>
                    <th align='right'>Unit</th>
                    <th align='right'>Subtotal</th>
                </tr></thead>
                <tbody>{items_html}</tbody>
            </table>
            <p style='margin-top:14px'>
                <b>Order Type:</b> {order.order_type}<br>
                <b>Payment:</b> {order.payment_method or '—'} ({order.payment_status})<br>
                <b>Voucher:</b> {order.voucher_code or '—'}
            </p>
            <p style='text-align:right'>
                Subtotal: ₱{order.subtotal:,.2f}<br>
                Discount: -₱{order.discount_amount:,.2f}<br>
                <span style='font-size:18px;font-weight:700'>Total: ₱{order.total_amount:,.2f}</span>
            </p>
            { ("<p style='color:#10B981'>✓ Confirmation email sent to "
               + str(order.email_sent_to) + "</p>") if order.email_sent_to else ""}
        """)
        v.addWidget(browser, 1)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        bot = QHBoxLayout(); bot.addStretch(1); bot.addWidget(close)
        v.addLayout(bot)

    def _build_timeline(self, order) -> QFrame:
        """Render a vertical timeline from the recorded status history.

        Falls back to a synthesized 'Pending' entry if the order pre-dates
        the history audit feature.
        """
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;}"
        )
        v = QVBoxLayout(frame)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(6)

        history = list(order.history)
        if not history:
            v.addWidget(QLabel("Order placed."))
            return frame

        for i, h in enumerate(history):
            row = QHBoxLayout()
            is_last = i == len(history) - 1
            if h.to_status == "Completed":
                color = "#10B981"
            elif h.to_status == "Cancelled":
                color = "#EF4444"
            elif is_last:
                color = "#4F46E5"
            else:
                color = "#9CA3AF"
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{color};font-size:14px;background:transparent;")
            row.addWidget(dot)

            label_map = {
                "Pending": "Order placed",
                "Processing": "In progress",
                "ReadyForPickup": "Ready for pickup",
                "ReadyForDelivery": "Out for delivery",
                "Completed": "Completed",
                "Cancelled": "Cancelled",
            }
            text = f"<b>{label_map.get(h.to_status, h.to_status)}</b>"
            if h.notes and h.notes != "Order placed":
                text += f" <span style='color:#6B7280'>· {h.notes}</span>"
            lbl = QLabel(text)
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setStyleSheet("background:transparent;")
            row.addWidget(lbl, 1)

            when = QLabel(h.created_at.strftime("%b %d, %H:%M"))
            when.setStyleSheet("color:#6B7280;font-size:11px;background:transparent;")
            row.addWidget(when)

            wrap = QWidget()
            wrap.setLayout(row)
            v.addWidget(wrap)
        return frame


class CustomerOrdersTab(QWidget):
    def __init__(self, customer: CustomerModel, parent=None):
        super().__init__(parent)
        self.customer = customer

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)

        title = QLabel("<h2 style='margin:0'>My Orders</h2>")
        v.addWidget(title)
        sub = QLabel("Track every order you have placed.")
        sub.setStyleSheet("color:#6B7280;font-size:12px;margin-bottom:8px;")
        v.addWidget(sub)
        v.addSpacing(6)

        self.list_box = QVBoxLayout()
        self.list_box.setSpacing(10)
        inner = QWidget()
        inner.setLayout(self.list_box)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        scroll.setWidget(inner)
        v.addWidget(scroll, 1)

    def refresh(self) -> None:
        # clear
        while self.list_box.count():
            it = self.list_box.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)

        rows = [o for o in order_service.list_orders()
                if o.customer_id == self.customer.customer_id]

        if not rows:
            empty = QLabel("You have not placed any orders yet.")
            empty.setStyleSheet("color:#9CA3AF;padding:40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_box.addWidget(empty)
            return

        for o in rows:
            self.list_box.addWidget(self._build_card(o))
        self.list_box.addStretch(1)

    def _make_click_handler(self, order):
        """Return a mousePressEvent handler that returns None (avoids sipBadCatcherResult)."""
        def handler(_event):
            OrderDetailDialog(order, self).exec()
        return handler

    def _build_card(self, order) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mousePressEvent = self._make_click_handler(order)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 12, 16, 12)

        head = QHBoxLayout()
        title = QLabel(f"<b>Order #{order.order_id}</b>")
        head.addWidget(title)
        head.addStretch(1)
        badge = QLabel(order.order_status)
        badge.setObjectName(_STATUS_BADGE.get(order.order_status, "chipNeutral"))
        head.addWidget(badge)
        type_chip = QLabel(order.order_type)
        type_chip.setObjectName("chipNeutral")
        head.addWidget(type_chip)
        cl.addLayout(head)

        date_lbl = QLabel(order.order_date.strftime("%b %d, %Y · %H:%M"))
        date_lbl.setStyleSheet("color:#6B7280;font-size:12px;")
        cl.addWidget(date_lbl)

        items = ", ".join(f"{it.product_name} ×{it.quantity}" for it in order.items)
        items_lbl = QLabel(items[:120] + ("…" if len(items) > 120 else ""))
        items_lbl.setStyleSheet("color:#374151;")
        items_lbl.setWordWrap(True)
        cl.addWidget(items_lbl)

        bot = QHBoxLayout()
        total = QLabel(f"<b>₱{order.total_amount:,.2f}</b>")
        total.setStyleSheet("font-size:16px;color:#4F46E5;font-weight:700;")
        bot.addWidget(total)
        bot.addStretch(1)
        view = QLabel("View details →")
        view.setStyleSheet("color:#6B7280;font-size:12px;")
        bot.addWidget(view)
        cl.addLayout(bot)
        return card
