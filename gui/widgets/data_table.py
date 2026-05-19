"""Reusable sortable / filterable table widget built on QTableWidget."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem
)


class DataTable(QTableWidget):
    """Light wrapper providing a few defaults and convenience helpers."""

    def __init__(self, headers: list[str], parent=None,
                 resize_mode: QHeaderView.ResizeMode = QHeaderView.ResizeMode.Stretch):
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(True)
        self.horizontalHeader().setSectionResizeMode(resize_mode)
        # Make sure both scrollbars are available when the contents need them.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollMode(self.ScrollMode.ScrollPerPixel)

    def set_rows(self, rows: list[list[str]], row_colors: list[QColor | None] | None = None) -> None:
        self.setSortingEnabled(False)
        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if row_colors and r < len(row_colors) and row_colors[r]:
                    item.setBackground(QBrush(row_colors[r]))
                self.setItem(r, c, item)
        self.setSortingEnabled(True)
