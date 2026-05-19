"""Promotions / discount-code management tab."""
from __future__ import annotations

from datetime import date

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget
)

from gui.widgets.data_table import DataTable
from gui.widgets import validators as V
from services import product_service, promotion_service


class PromotionEditor(QDialog):
    def __init__(self, parent=None, data: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Promotion" if data else "Add Promotion")
        self.setMinimumSize(520, 600)

        self.name = QLineEdit(data.get("name", "") if data else "")
        self.desc = QTextEdit(data.get("description", "") if data else "")
        self.desc.setMaximumHeight(70)
        self.code = QLineEdit(data.get("code", "") if data else "")
        self.discount_type = QComboBox()
        self.discount_type.addItems(["Percentage", "FixedAmount"])
        if data:
            self.discount_type.setCurrentText(data.get("discount_type", "Percentage"))
        self.discount_value = QDoubleSpinBox()
        self.discount_value.setRange(0.0, 100000.0)
        self.discount_value.setValue(float(data.get("discount_value", 0.0)) if data else 0.0)
        self.min_amount = QDoubleSpinBox()
        self.min_amount.setRange(0.0, 1000000.0)
        self.min_amount.setPrefix("₱ ")
        self.min_amount.setValue(float(data.get("minimum_order_amount", 0.0)) if data else 0.0)

        self.usage_unlimited = QCheckBox("Unlimited usage")
        self.usage_limit = QSpinBox()
        self.usage_limit.setRange(0, 1000000)
        self.usage_limit.setValue(int(data.get("usage_limit") or 0) if data else 0)
        if not data or data.get("usage_limit") is None:
            self.usage_unlimited.setChecked(True)
        self.usage_unlimited.toggled.connect(lambda v: self.usage_limit.setEnabled(not v))
        self.usage_limit.setEnabled(not self.usage_unlimited.isChecked())

        self.start = QDateEdit()
        self.start.setCalendarPopup(True)
        self.start.setDate(QDate.currentDate())
        self.end = QDateEdit()
        self.end.setCalendarPopup(True)
        self.end.setDate(QDate.currentDate().addMonths(1))
        if data:
            if data.get("start_date"):
                self.start.setDate(QDate(data["start_date"].year, data["start_date"].month, data["start_date"].day))
            if data.get("end_date"):
                self.end.setDate(QDate(data["end_date"].year, data["end_date"].month, data["end_date"].day))

        self.is_active = QCheckBox("Active")
        self.is_active.setChecked(bool(data.get("is_active", True)) if data else True)

        # product list
        self.product_list = QListWidget()
        self.product_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        scoped = set(data.get("product_ids", []) if data else [])
        for p in product_service.list_products(status="All"):
            li = QListWidgetItem(f"{p.product_name} (₱{p.product_price:,.2f})")
            li.setData(Qt.ItemDataRole.UserRole, p.product_id)
            li.setFlags(li.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            li.setCheckState(Qt.CheckState.Checked if p.product_id in scoped else Qt.CheckState.Unchecked)
            self.product_list.addItem(li)

        form = QFormLayout()
        form.addRow("Name *", self.name)
        form.addRow("Description", self.desc)
        form.addRow("Promo Code *", self.code)
        form.addRow("Discount Type", self.discount_type)
        form.addRow("Discount Value", self.discount_value)
        form.addRow("Minimum Order", self.min_amount)
        form.addRow(self.usage_unlimited)
        form.addRow("Usage Limit", self.usage_limit)
        form.addRow("Start Date", self.start)
        form.addRow("End Date", self.end)
        form.addRow(self.is_active)

        prod_box = QGroupBox("Apply to specific products (leave all unchecked = all products)")
        prod_layout = QVBoxLayout(prod_box)
        prod_layout.addWidget(self.product_list)

        save = QPushButton("Save")
        save.setObjectName("primaryBtn")
        save.clicked.connect(self._save)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(cancel)
        btns.addWidget(save)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(prod_box, 1)
        root.addLayout(btns)
        V.install_error_qss(self)

    def _save(self):
        V.clear_errors([self.name, self.code, self.discount_value,
                        self.min_amount, self.usage_limit, self.start, self.end])
        errors: list[tuple[object, str]] = []
        e = V.text_length(self.name.text(), "Name", minimum=2, maximum=80)
        if e: errors.append((self.name, e))
        e = V.promo_code(self.code.text())
        if e: errors.append((self.code, e))

        dtype = self.discount_type.currentText()
        if dtype == "Percentage":
            e = V.positive_number(self.discount_value.value(),
                                  "Discount value", maximum=100)
        else:
            e = V.positive_number(self.discount_value.value(),
                                  "Discount value", maximum=1_000_000)
        if e: errors.append((self.discount_value, e))

        e = V.positive_number(self.min_amount.value(), "Minimum order",
                              allow_zero=True, maximum=1_000_000)
        if e: errors.append((self.min_amount, e))

        if not self.usage_unlimited.isChecked():
            e = V.positive_int(self.usage_limit.value(), "Usage limit",
                               allow_zero=False, maximum=1_000_000)
            if e: errors.append((self.usage_limit, e))

        e = V.date_range(self.start.date().toPyDate(),
                         self.end.date().toPyDate())
        if e:
            errors.append((self.end, e))

        if len(self.desc.toPlainText().strip()) > 300:
            errors.append((self.desc, "Description must be at most 300 characters."))

        if errors:
            for widget, _ in errors:
                V.mark_error(widget, True)
            QMessageBox.warning(self, "Check the form", errors[0][1])
            return
        self.accept()

    def values(self) -> dict:
        pids = []
        for i in range(self.product_list.count()):
            li = self.product_list.item(i)
            if li.checkState() == Qt.CheckState.Checked:
                pids.append(li.data(Qt.ItemDataRole.UserRole))
        return {
            "name": self.name.text().strip(),
            "description": self.desc.toPlainText().strip(),
            "discount_type": self.discount_type.currentText(),
            "discount_value": self.discount_value.value(),
            "minimum_order_amount": self.min_amount.value(),
            "code": self.code.text().strip(),
            "usage_limit": None if self.usage_unlimited.isChecked() else self.usage_limit.value(),
            "start_date": self.start.date().toPyDate(),
            "end_date": self.end.date().toPyDate(),
            "is_active": self.is_active.isChecked(),
            "product_ids": pids,
        }


class PromotionsTab(QWidget):
    HEADERS = [
        "ID", "Name", "Code", "Type", "Value", "Min Order",
        "Used / Limit", "Start", "End", "Status",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        add = QPushButton("+ Add Promotion")
        add.setObjectName("primaryBtn")
        add.clicked.connect(self._add)
        bar.addWidget(add)
        bar.addStretch(1)
        ref = QPushButton("Refresh")
        ref.clicked.connect(self.refresh)
        bar.addWidget(ref)
        layout.addLayout(bar)

        self.table = DataTable(self.HEADERS)
        self.table.cellDoubleClicked.connect(self._edit)
        layout.addWidget(self.table)

        action_row = QHBoxLayout()
        edit = QPushButton("Edit")
        edit.clicked.connect(self._edit)
        delete = QPushButton("Delete")
        delete.setObjectName("dangerBtn")
        delete.clicked.connect(self._delete)
        action_row.addStretch(1)
        action_row.addWidget(edit)
        action_row.addWidget(delete)
        layout.addLayout(action_row)

        self.refresh()

    def refresh(self) -> None:
        rows = promotion_service.list_promotions()
        body = []
        for p in rows:
            usage = f"{p.used_count} / {p.usage_limit if p.usage_limit is not None else '∞'}"
            value_str = (f"{p.discount_value:.0f}%" if p.discount_type == "Percentage"
                         else f"₱{p.discount_value:,.2f}")
            body.append([
                str(p.promotion_id), p.promotion_name, p.code,
                p.discount_type, value_str,
                f"₱{p.minimum_order_amount:,.2f}", usage,
                p.start_date.strftime("%Y-%m-%d") if p.start_date else "—",
                p.end_date.strftime("%Y-%m-%d") if p.end_date else "—",
                "Active" if p.is_active else "Inactive",
            ])
        self.table.set_rows(body)

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())

    def _add(self) -> None:
        dlg = PromotionEditor(self)
        if dlg.exec():
            try:
                promotion_service.add_promotion(**dlg.values())
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _edit(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        rows = {p.promotion_id: p for p in promotion_service.list_promotions()}
        p = rows.get(pid)
        if not p:
            return
        data = {
            "name": p.promotion_name, "description": p.promotion_description,
            "discount_type": p.discount_type, "discount_value": p.discount_value,
            "minimum_order_amount": p.minimum_order_amount, "code": p.code,
            "usage_limit": p.usage_limit, "start_date": p.start_date,
            "end_date": p.end_date, "is_active": p.is_active,
            "product_ids": p.product_ids,
        }
        dlg = PromotionEditor(self, data)
        if dlg.exec():
            try:
                promotion_service.update_promotion(pid, **dlg.values())
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _delete(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        if QMessageBox.question(self, "Confirm", "Delete this promotion?") == QMessageBox.StandardButton.Yes:
            promotion_service.delete_promotion(pid)
            self.refresh()
