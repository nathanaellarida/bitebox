"""Lightweight toast / snackbar notification.

Pops a small rounded panel in the bottom-right of any parent widget,
fades in, holds for a moment, then fades out. Used for low-stakes
confirmations like "Added to cart" so the user is never blocked by a
modal dialog.
"""
from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve, QPoint, QPropertyAnimation, QTimer, Qt,
)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QWidget,
)


class Toast(QWidget):
    """Floating, auto-dismissing notification chip.

    Use :meth:`Toast.show_message` to display one without managing the
    instance yourself.
    """

    LEVELS: dict[str, tuple[str, str]] = {
        "success": ("#10B981", "#FFFFFF"),
        "info":    ("#1E1B4B", "#FFFFFF"),
        "warning": ("#F59E0B", "#FFFFFF"),
        "error":   ("#EF4444", "#FFFFFF"),
    }

    def __init__(self, parent: QWidget, message: str,
                 level: str = "info", duration_ms: int = 2400) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        bg, fg = self.LEVELS.get(level, self.LEVELS["info"])
        self.setStyleSheet(
            f"QWidget{{background:{bg};color:{fg};border-radius:14px;}}"
            f"QLabel{{background:transparent;color:{fg};font-weight:600;"
            "font-size:13px;padding:10px 18px;}}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(message)
        label.setWordWrap(False)
        layout.addWidget(label)

        # Soft shadow so it lifts off the page on light backgrounds.
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(shadow)

        self.adjustSize()
        self._reposition()
        self._duration_ms = duration_ms

        # Fade in
        self.setWindowOpacity(0.0)
        self._fade_in = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_in.setDuration(180)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Fade out
        self._fade_out = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_out.setDuration(220)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self.close)

    @classmethod
    def show_message(cls, parent: QWidget, message: str,
                     level: str = "info", duration_ms: int = 2400) -> "Toast":
        """Construct, position, animate, and return a Toast in one step."""
        toast = cls(parent, message, level=level, duration_ms=duration_ms)
        toast.show()
        toast.raise_()
        toast._fade_in.start()
        QTimer.singleShot(duration_ms, toast._fade_out.start)
        return toast

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        margin = 24
        x = max(margin, parent.width() - self.width() - margin)
        y = max(margin, parent.height() - self.height() - margin)
        self.move(QPoint(x, y))

    def parentResized(self) -> None:
        """Public hook so windows can ask a live toast to reposition."""
        self._reposition()
