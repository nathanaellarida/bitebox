"""KPI stat card widget."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatCard(QFrame):
    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setMinimumHeight(90)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("statTitle")
        self.value_lbl = QLabel(value)
        self.value_lbl.setObjectName("statValue")
        self.value_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.value_lbl)
        layout.addStretch(1)

    def set_value(self, value: str) -> None:
        self.value_lbl.setText(value)
