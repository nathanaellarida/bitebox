"""Icon button with an overlaid numeric badge.

Used in the customer header so the cart icon shows the current number
of items in the cart. The badge auto-hides when the count is 0.
"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QPushButton


class BadgedIconButton(QPushButton):
    """A QPushButton that paints a small red circular badge with a count.

    Set the count via :meth:`set_count`; values <= 0 hide the badge.
    Counts greater than 99 render as ``99+`` so the badge stays compact.
    """

    BADGE_COLOR = QColor("#EF4444")
    BADGE_TEXT_COLOR = QColor("#FFFFFF")
    BADGE_BORDER_COLOR = QColor("#FFFFFF")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._count = 0

    def set_count(self, count: int) -> None:
        count = max(0, int(count))
        if count == self._count:
            return
        self._count = count
        self.update()

    def count(self) -> int:
        return self._count

    def paintEvent(self, event):  # noqa: D401 - Qt override
        super().paintEvent(event)
        if self._count <= 0:
            return

        text = "99+" if self._count > 99 else str(self._count)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Badge sized to fit the text; minimum size keeps single digits round.
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSize(8)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        text_w = metrics.horizontalAdvance(text)
        text_h = metrics.height()
        diameter = max(16, text_w + 8)
        height = max(16, text_h)

        # Anchor the badge to the top-right corner with a tiny inset so the
        # white border is visible against any header background.
        x = self.width() - diameter - 2
        y = 2
        rect = QRectF(x, y, diameter, height)

        painter.setPen(QPen(self.BADGE_BORDER_COLOR, 1.5))
        painter.setBrush(QBrush(self.BADGE_COLOR))
        painter.drawRoundedRect(rect, height / 2, height / 2)

        painter.setPen(self.BADGE_TEXT_COLOR)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
