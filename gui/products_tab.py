"""Product management tab with full CRUD and option groups."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QTextEdit, QVBoxLayout, QWidget
)

from gui.widgets.data_table import DataTable
from gui.widgets import validators as V
from models.staff import StaffModel
from services import category_service, product_service


class OptionGroupEditor(QGroupBox):
    """One option group with a list of items, used inside ProductEditor."""

    def __init__(self, group_data: dict | None = None, parent=None):
        super().__init__("Option Group", parent)
        self.items: list[dict] = []

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.required = QCheckBox("Required")
        self.max_choices = QSpinBox()
        self.max_choices.setRange(1, 20)
        form.addRow("Group Name", self.name_edit)
        form.addRow("Max Choices", self.max_choices)
        form.addRow(self.required)
        layout.addLayout(form)

        self.items_box = QVBoxLayout()
        layout.addLayout(self.items_box)

        add_item_btn = QPushButton("+ Add Item")
        add_item_btn.clicked.connect(lambda: self._add_item_row())
        layout.addWidget(add_item_btn)

        if group_data:
            self.name_edit.setText(group_data.get("group_name", ""))
            self.required.setChecked(bool(group_data.get("is_required", False)))
            self.max_choices.setValue(int(group_data.get("max_choices", 1)))
            for it in group_data.get("items", []):
                self._add_item_row(it.get("option_name", ""), float(it.get("additional_price", 0.0)))
        else:
            self._add_item_row()

    def _add_item_row(self, name: str = "", price: float = 0.0) -> None:
        row = QHBoxLayout()
        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("Option name (e.g. Large)")
        price_edit = QDoubleSpinBox()
        price_edit.setRange(0.0, 99999.0)
        price_edit.setPrefix("+₱ ")
        price_edit.setValue(price)
        rm_btn = QPushButton("✕")
        rm_btn.setMaximumWidth(30)

        container = QWidget()
        container.setLayout(row)
        row.addWidget(name_edit, 1)
        row.addWidget(price_edit)
        row.addWidget(rm_btn)
        self.items_box.addWidget(container)

        item_ref = {"name_edit": name_edit, "price_edit": price_edit, "container": container}
        self.items.append(item_ref)
        rm_btn.clicked.connect(lambda: self._remove_item(item_ref))

    def _remove_item(self, item_ref: dict) -> None:
        item_ref["container"].setParent(None)
        self.items.remove(item_ref)

    def to_dict(self) -> dict:
        return {
            "group_name": self.name_edit.text().strip(),
            "is_required": self.required.isChecked(),
            "max_choices": self.max_choices.value(),
            "items": [
                {
                    "option_name": it["name_edit"].text().strip(),
                    "additional_price": it["price_edit"].value(),
                }
                for it in self.items if it["name_edit"].text().strip()
            ],
        }


class ProductEditor(QDialog):
    def __init__(self, parent=None, data: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Product" if data else "Add Product")
        self.setMinimumSize(560, 640)

        self.image_path = data.get("product_image_path", "") if data else ""

        # categories
        self.categories = category_service.list_categories()

        self.name_edit = QLineEdit(data.get("product_name", "") if data else "")
        self.desc_edit = QTextEdit(data.get("product_description", "") if data else "")
        self.desc_edit.setMaximumHeight(80)
        self.price_edit = QDoubleSpinBox()
        self.price_edit.setRange(0.0, 999999.99)
        self.price_edit.setPrefix("₱ ")
        self.price_edit.setValue(float(data.get("product_price", 0.0)) if data else 0.0)
        self.qty_edit = QSpinBox()
        self.qty_edit.setRange(0, 1000000)
        self.qty_edit.setValue(int(data.get("quantity_on_hand", 0)) if data else 0)

        self.cat_combo = QComboBox()
        self.cat_combo.addItem("(none)", None)
        for c in self.categories:
            self.cat_combo.addItem(c["category_name"], c["category_id"])
        if data and data.get("category_id"):
            idx = self.cat_combo.findData(data["category_id"])
            if idx >= 0:
                self.cat_combo.setCurrentIndex(idx)

        # Image picker — thumbnail preview + Change / Remove
        self._image_changed = False  # only push to service if user touched it
        self._existing_image_path = self.image_path  # may be a saved file
        self.image_thumb = QLabel()
        self.image_thumb.setFixedSize(140, 100)
        self.image_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_thumb.setStyleSheet(
            "QLabel{background:#F3F4F6;border:1px dashed #D1D5DB;"
            "border-radius:8px;color:#9CA3AF;}"
        )
        self.image_caption = QLabel()
        self.image_caption.setStyleSheet("color:#6B7280;font-size:11px;")
        self.image_caption.setWordWrap(True)

        change_btn = QPushButton("Change Image…")
        change_btn.clicked.connect(self._pick_image)
        self.remove_img_btn = QPushButton("Remove")
        self.remove_img_btn.setObjectName("dangerBtn")
        self.remove_img_btn.clicked.connect(self._remove_image)

        img_btns = QVBoxLayout()
        img_btns.addWidget(change_btn)
        img_btns.addWidget(self.remove_img_btn)
        img_btns.addWidget(self.image_caption)
        img_btns.addStretch(1)

        img_row = QHBoxLayout()
        img_row.addWidget(self.image_thumb)
        img_row.addLayout(img_btns, 1)

        self._refresh_image_preview()

        form = QFormLayout()
        form.addRow("Name *", self.name_edit)
        form.addRow("Category", self.cat_combo)
        form.addRow("Price *", self.price_edit)
        form.addRow("Qty on Hand", self.qty_edit)
        form.addRow("Description", self.desc_edit)
        form.addRow("Image", img_row)

        # option groups
        self.groups_layout = QVBoxLayout()
        self.group_editors: list[OptionGroupEditor] = []
        if data:
            for g in data.get("option_groups", []):
                self._add_group(g)

        add_group_btn = QPushButton("+ Add Option Group")
        add_group_btn.clicked.connect(lambda: self._add_group())

        # scroll
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.addLayout(form)
        inner_layout.addWidget(QLabel("Option Groups (optional)"))
        inner_layout.addLayout(self.groups_layout)
        inner_layout.addWidget(add_group_btn)
        inner_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)

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
        root.addWidget(scroll, 1)
        root.addLayout(btns)
        V.install_error_qss(self)

    def _add_group(self, data: dict | None = None) -> None:
        editor = OptionGroupEditor(data)
        self.group_editors.append(editor)
        self.groups_layout.addWidget(editor)

    def _pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose product image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if path:
            self.image_path = path
            self._image_changed = True
            self._refresh_image_preview()

    def _remove_image(self) -> None:
        if not self.image_path and not self._existing_image_path:
            return
        if QMessageBox.question(self, "Remove image",
                                "Remove this product's image?") \
                != QMessageBox.StandardButton.Yes:
            return
        self.image_path = ""
        self._image_changed = True
        self._refresh_image_preview()

    def _refresh_image_preview(self) -> None:
        from pathlib import Path as _P
        from PyQt6.QtGui import QPixmap
        path = self.image_path
        if path and _P(path).exists():
            pix = QPixmap(path)
            if not pix.isNull():
                pix = pix.scaled(
                    140, 100,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.image_thumb.setPixmap(pix)
                self.image_thumb.setStyleSheet(
                    "QLabel{background:#F3F4F6;border:1px solid #E5E7EB;"
                    "border-radius:8px;}"
                )
                name = _P(path).name
                self.image_caption.setText(
                    f"<b>{name}</b><br><span style='color:#9CA3AF'>{path}</span>"
                )
                self.image_caption.setTextFormat(Qt.TextFormat.RichText)
                self.remove_img_btn.setEnabled(True)
                return
        self.image_thumb.setPixmap(QPixmap())
        self.image_thumb.setText("No image")
        self.image_thumb.setStyleSheet(
            "QLabel{background:#F3F4F6;border:1px dashed #D1D5DB;"
            "border-radius:8px;color:#9CA3AF;}"
        )
        self.image_caption.setText("PNG, JPG, JPEG, GIF or WEBP")
        self.image_caption.setTextFormat(Qt.TextFormat.PlainText)
        self.remove_img_btn.setEnabled(bool(self._existing_image_path))

    def _save(self):
        V.clear_errors([self.name_edit, self.price_edit, self.qty_edit,
                        self.desc_edit])
        errors: list[tuple[object, str]] = []
        e = V.text_length(self.name_edit.text(), "Product name",
                          minimum=2, maximum=80)
        if e: errors.append((self.name_edit, e))
        e = V.positive_number(self.price_edit.value(), "Price",
                              maximum=999999.99)
        if e: errors.append((self.price_edit, e))
        e = V.positive_int(self.qty_edit.value(), "Qty on hand",
                           allow_zero=True, maximum=1_000_000)
        if e: errors.append((self.qty_edit, e))
        if len(self.desc_edit.toPlainText().strip()) > 500:
            errors.append((self.desc_edit, "Description must be at most 500 characters."))

        # Option groups: each name required, each item name required
        for grp in self.group_editors:
            data = grp.to_dict()
            if not data["group_name"]:
                errors.append((grp, "Each option group needs a name."))
                continue
            if data["max_choices"] < 1:
                errors.append((grp, f"'{data['group_name']}' max choices must be at least 1."))
            if not data["items"]:
                errors.append((grp, f"Option group '{data['group_name']}' has no items."))
            for it in data["items"]:
                if it["additional_price"] < 0:
                    errors.append((grp, f"Item '{it['option_name']}' price cannot be negative."))

        if errors:
            for widget, _ in errors:
                if hasattr(widget, "setProperty"):
                    V.mark_error(widget, True)
            QMessageBox.warning(self, "Check the form", errors[0][1])
            return
        self.accept()

    def values(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "price": self.price_edit.value(),
            "category_id": self.cat_combo.currentData(),
            "description": self.desc_edit.toPlainText().strip(),
            "quantity_on_hand": self.qty_edit.value(),
            # image_path is only meaningful if the user touched it; we
            # signal that with image_changed so callers can decide
            # whether to clear or keep the existing file.
            "image_path": self.image_path if self._image_changed else None,
            "image_changed": self._image_changed,
            "option_groups": [g.to_dict() for g in self.group_editors],
        }


class ProductsTab(QWidget):
    HEADERS = ["ID", "Name", "Category", "Price", "Qty On Hand", "Qty Sold", "Status"]

    def __init__(self, current_staff: StaffModel, parent=None):
        super().__init__(parent)
        self.current_staff = current_staff

        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search products…")
        self.search.textChanged.connect(self.refresh)

        self.cat_filter = QComboBox()
        self.cat_filter.addItem("All categories", None)
        for c in category_service.list_categories():
            self.cat_filter.addItem(c["category_name"], c["category_id"])
        self.cat_filter.currentIndexChanged.connect(self.refresh)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Active", "Inactive", "Deleted"])
        self.status_filter.currentTextChanged.connect(self.refresh)

        add_btn = QPushButton("+ Add Product")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._add)

        toolbar.addWidget(self.search, 2)
        toolbar.addWidget(QLabel("Category"))
        toolbar.addWidget(self.cat_filter, 1)
        toolbar.addWidget(QLabel("Status"))
        toolbar.addWidget(self.status_filter, 1)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        self.table = DataTable(self.HEADERS)
        self.table.cellDoubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

        action_row = QHBoxLayout()
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._edit_selected)
        toggle_btn = QPushButton("Activate / Deactivate")
        toggle_btn.clicked.connect(self._toggle_active)
        delete_btn = QPushButton("Delete (soft)")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.clicked.connect(self._delete)
        recover_btn = QPushButton("Recover")
        recover_btn.clicked.connect(self._recover)
        perm_btn = QPushButton("Permanent Delete (Admin)")
        perm_btn.setObjectName("dangerBtn")
        perm_btn.clicked.connect(self._perm_delete)
        perm_btn.setVisible(self.current_staff.role == "Admin")

        action_row.addStretch(1)
        action_row.addWidget(edit_btn)
        action_row.addWidget(toggle_btn)
        action_row.addWidget(recover_btn)
        action_row.addWidget(delete_btn)
        action_row.addWidget(perm_btn)
        layout.addLayout(action_row)

        self.refresh()

    def refresh(self) -> None:
        rows = product_service.list_products(
            category_id=self.cat_filter.currentData(),
            status=self.status_filter.currentText(),
            search=self.search.text(),
        )
        body, colors = [], []
        for p in rows:
            status = "Deleted" if p.is_deleted else ("Active" if p.is_active else "Inactive")
            body.append([
                str(p.product_id), p.product_name, p.category_name,
                f"₱{p.product_price:,.2f}", str(p.quantity_on_hand),
                str(p.quantity_sold), status,
            ])
            colors.append(QColor("#fee2e2") if (p.quantity_on_hand <= 5 and not p.is_deleted) else None)
        self.table.set_rows(body, colors)

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())

    def _add(self) -> None:
        dlg = ProductEditor(self)
        if dlg.exec():
            v = dlg.values()
            try:
                product_service.add_product(**v)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _edit_selected(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        p = product_service.get_product(pid)
        if not p:
            return
        data = {
            "product_name": p.product_name,
            "product_description": p.product_description or "",
            "product_price": p.product_price,
            "category_id": p.category_id,
            "quantity_on_hand": p.quantity_on_hand,
            "product_image_path": p.product_image_path or "",
            "option_groups": [
                {
                    "group_name": g.group_name,
                    "is_required": g.is_required,
                    "max_choices": g.max_choices,
                    "items": [
                        {"option_name": i.option_name, "additional_price": i.additional_price}
                        for i in g.items
                    ],
                }
                for g in p.option_groups
            ],
        }
        dlg = ProductEditor(self, data)
        if dlg.exec():
            v = dlg.values()
            try:
                product_service.update_product(pid, **v)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _toggle_active(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        product_service.toggle_active(pid)
        self.refresh()

    def _delete(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        if QMessageBox.question(self, "Confirm", "Soft-delete this product?") == QMessageBox.StandardButton.Yes:
            product_service.soft_delete_product(pid, self.current_staff.full_name)
            self.refresh()

    def _recover(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        product_service.recover_product(pid)
        self.refresh()

    def _perm_delete(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        if QMessageBox.question(
            self, "Permanent Delete",
            "This cannot be undone and may break order history. Continue?"
        ) == QMessageBox.StandardButton.Yes:
            try:
                product_service.permanent_delete_product(pid)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
