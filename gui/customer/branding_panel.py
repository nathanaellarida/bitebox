"""Reusable branding panel for the login windows.

Paints a full-bleed image with a dark gradient overlay so the white text
remains readable. Falls back to the brand color (#1E1B4B) if no image
is supplied.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QFrame


class BrandingPanel(QFrame):
    """Image-backed brand panel with a dark left-to-right gradient overlay."""

    def __init__(self, image_filename: str = "branding_image.jpg", parent=None):
        super().__init__(parent)
        self.setObjectName("brandingPanel")
        self._pixmap: Optional[QPixmap] = self._load_image(image_filename)

    def _load_image(self, filename: str) -> Optional[QPixmap]:
        from gui.customer.assets_loader import customer_image
        # Try the requested file first, then sensible defaults
        candidates = [filename, "branding_image.jpg", "branding_image.png",
                      "hero_banner.jpg", "hero_banner.png"]
        for name in candidates:
            pix = customer_image(name)
            if pix is not None:
                return pix
        return None

    def paintEvent(self, _event):  # noqa
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1) Image cover (or solid fallback)
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
        else:
            painter.fillRect(self.rect(), QColor("#1E1B4B"))

        # 2) Strong dark overlay so text is always legible
        grad = QLinearGradient(QPointF(0, 0), QPointF(self.width(), 0))
        grad.setColorAt(0.0, QColor(15, 12, 40, 235))
        grad.setColorAt(1.0, QColor(15, 12, 40, 200))
        painter.fillRect(self.rect(), QBrush(grad))

        # 3) Subtle top-down vignette to deepen the corners
        vert = QLinearGradient(QPointF(0, 0), QPointF(0, self.height()))
        vert.setColorAt(0.0, QColor(0, 0, 0, 60))
        vert.setColorAt(0.5, QColor(0, 0, 0, 0))
        vert.setColorAt(1.0, QColor(0, 0, 0, 80))
        painter.fillRect(self.rect(), QBrush(vert))
