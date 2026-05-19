"""Notifications popup — recent activity for the logged-in customer.

Pulls from the order_status_history audit trail so every entry is a
real database event (order placed, processing, ready, completed, etc.).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget
)

from models.customer import CustomerModel
from services import order_service


_ICON_MAP = {
    "Pending": ("fa5s.receipt", "#1E1B4B", "Order placed"),
    "Processing": ("fa5s.utensils", "#3B82F6", "Order is being prepared"),
    "ReadyForPickup": ("fa5s.shopping-bag", "#F59E0B", "Ready for pickup"),
    "ReadyForDelivery": ("fa5s.truck", "#F59E0B", "Out for delivery"),
    "Completed": ("fa5s.check-circle", "#10B981", "Order completed"),
    "Cancelled": ("fa5s.times-circle", "#EF4444", "Order cancelled"),
}


def _format_relative(when: datetime) -> str:
    delta = datetime.now() - when
    if delta < timedelta(seconds=60):
        return "just now"
    if delta < timedelta(minutes=60):
        m = int(delta.total_seconds() // 60)
        return f"{m} min ago"
    if delta < timedelta(hours=24):
        h = int(delta.total_seconds() // 3600)
        return f"{h} hour{'s' if h != 1 else ''} ago"
    if delta < timedelta(days=7):
        d = delta.days
        return f"{d} day{'s' if d != 1 else ''} ago"
    return when.strftime("%b %d")


class _NotificationRow(QFrame):
    def __init__(self, icon_name: str, color: str, title: str,
                 detail: str, when_label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("notificationRow")
        self.setStyleSheet(
            "QFrame#notificationRow{background:transparent;border:none;}"
        )
        l = QHBoxLayout(self)
        l.setContentsMargins(4, 8, 4, 8)
        l.setSpacing(12)

        # Tinted icon disc
        try:
            import qtawesome as qta
            icon_lbl = QLabel()
            icon_lbl.setFixedSize(36, 36)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_lbl.setPixmap(qta.icon(icon_name, color=color).pixmap(20, 20))
            icon_lbl.setStyleSheet(
                f"QLabel{{background:{color}1A;border-radius:18px;}}"
            )
        except Exception:
            icon_lbl = QLabel("•")
            icon_lbl.setFixedSize(36, 36)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_lbl.setStyleSheet(f"color:{color};font-size:18px;background:{color}1A;border-radius:18px;")
        l.addWidget(icon_lbl)

        # Text column
        body = QVBoxLayout()
        body.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-weight:700;color:#111827;background:transparent;")
        detail_lbl = QLabel(detail)
        detail_lbl.setStyleSheet("color:#6B7280;font-size:12px;background:transparent;")
        detail_lbl.setWordWrap(True)
        body.addWidget(title_lbl)
        body.addWidget(detail_lbl)
        l.addLayout(body, 1)

        when_lbl = QLabel(when_label)
        when_lbl.setStyleSheet("color:#9CA3AF;font-size:11px;background:transparent;")
        when_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        l.addWidget(when_lbl)


class NotificationsPanel(QDialog):
    """Popup-style frameless dialog anchored under the bell icon."""

    def __init__(self, customer: CustomerModel, anchor_widget=None, parent=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(380, 480)

        # Position under the anchor button
        if anchor_widget is not None:
            top_left = anchor_widget.mapToGlobal(
                anchor_widget.rect().bottomLeft()
            )
            self.move(top_left.x() - self.width() + anchor_widget.width(),
                      top_left.y() + 6)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:#FFFFFF;border:1px solid #E5E7EB;border-radius:16px;}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("Notifications")
        title.setStyleSheet("font-size:16px;font-weight:800;color:#111827;background:transparent;")
        head.addWidget(title)
        head.addStretch(1)
        close = QPushButton("✕")
        close.setStyleSheet(
            "QPushButton{background:transparent;border:none;color:#9CA3AF;font-size:16px;}"
            "QPushButton:hover{color:#111827;}"
        )
        close.setFixedSize(24, 24)
        close.clicked.connect(self.accept)
        head.addWidget(close)
        cl.addLayout(head)

        rows_layout = QVBoxLayout()
        rows_layout.setSpacing(8)

        events = self._gather_events()
        if not events:
            empty = QLabel("No activity yet.\nPlace your first order to see updates here.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color:#9CA3AF;padding:60px 0;background:transparent;")
            rows_layout.addWidget(empty)
        else:
            for ev in events:
                rows_layout.addWidget(_NotificationRow(*ev))
            rows_layout.addStretch(1)

        rows_wrap = QWidget()
        rows_wrap.setLayout(rows_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        scroll.setWidget(rows_wrap)
        cl.addWidget(scroll, 1)

        outer.addWidget(card)

    def _gather_events(self) -> list[tuple[str, str, str, str, str]]:
        """Collect status changes for this customer's orders, newest first."""
        events: list[tuple[datetime, tuple[str, str, str, str, str]]] = []
        my_orders = [
            o for o in order_service.list_orders()
            if o.customer_id == self.customer.customer_id
        ]
        for o in my_orders:
            order = order_service.get_order(o.order_id)
            if not order:
                continue
            for h in order.history:
                meta = _ICON_MAP.get(h.to_status)
                if not meta:
                    continue
                icon, color, title = meta
                detail = f"Order #{order.order_id} — {h.notes or h.to_status}"
                when_lbl = _format_relative(h.created_at)
                events.append(
                    (h.created_at, (icon, color, title, detail, when_lbl))
                )
            # Email-sent event surfaces too
            if order.email_sent_at and order.email_sent_to:
                events.append(
                    (order.email_sent_at,
                     ("fa5s.envelope", "#1E1B4B",
                      "Confirmation email sent",
                      f"Order #{order.order_id} sent to {order.email_sent_to}",
                      _format_relative(order.email_sent_at)))
                )
        events.sort(key=lambda x: x[0], reverse=True)
        return [e[1] for e in events[:25]]
