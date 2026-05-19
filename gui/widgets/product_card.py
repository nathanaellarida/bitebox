"""Product card widget for the New Order catalog grid."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from models.product import ProductModel


class ProductCard(QFrame):
    """Small clickable card showing image, name, price, qty and Add button."""

    add_clicked = pyqtSignal(int)  # product_id

    def __init__(self, product: ProductModel, parent=None):
        super().__init__(parent)
        self.product = product
        self.setObjectName("statCard")
        self.setFixedSize(170, 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        img_label = QLabel()
        img_label.setFixedSize(150, 110)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setStyleSheet("background:#f3f4f6;border-radius:6px;")
        if product.product_image_path and Path(product.product_image_path).exists():
            pix = QPixmap(product.product_image_path)
            if not pix.isNull():
                img_label.setPixmap(pix.scaled(
                    150, 110, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            else:
                img_label.setText("No image")
        else:
            img_label.setText("No image")
        layout.addWidget(img_label, alignment=Qt.AlignmentFlag.AlignCenter)

        name_lbl = QLabel(product.product_name)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet("font-weight:600;")
        layout.addWidget(name_lbl)

        meta_text = f"₱{product.product_price:,.2f} · Stock: {product.quantity_on_hand}"
        if product.option_groups:
            meta_text += " · ⚙"
        meta_lbl = QLabel(meta_text)
        meta_lbl.setStyleSheet("color:#6b7280;font-size:11px;")
        layout.addWidget(meta_lbl)

        btn = QPushButton("Add")
        btn.setObjectName("primaryBtn")
        btn.clicked.connect(lambda: self.add_clicked.emit(product.product_id))
        if product.quantity_on_hand <= 0:
            btn.setEnabled(False)
            btn.setText("Out of stock")
        layout.addWidget(btn)
