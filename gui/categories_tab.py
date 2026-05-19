"""Category management tab."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout, QInputDialog, QMessageBox, QPushButton, QVBoxLayout, QWidget
)

from gui.widgets.data_table import DataTable
from gui.widgets import validators as V
from models.staff import StaffModel
from services import category_service


class CategoriesTab(QWidget):
    HEADERS = ["ID", "Name", "Products", "Status", "Actions"]

    def __init__(self, current_staff: StaffModel | None = None, parent=None):
        super().__init__(parent)
        self.current_staff = current_staff
        is_admin = bool(current_staff and current_staff.role == "Admin")

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        add_btn = QPushButton("+ Add Category")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._add)
        toolbar.addWidget(add_btn)
        toolbar.addStretch(1)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)
        layout.addLayout(toolbar)

        self.table = DataTable(self.HEADERS)
        self.table.cellDoubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

        action_row = QHBoxLayout()
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._edit_selected)
        del_btn = QPushButton("Delete (soft)")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._delete_selected)
        rec_btn = QPushButton("Recover")
        rec_btn.clicked.connect(self._recover_selected)
        action_row.addStretch(1)
        action_row.addWidget(edit_btn)
        action_row.addWidget(rec_btn)
        action_row.addWidget(del_btn)
        if is_admin:
            perm_btn = QPushButton("Permanent Delete (Admin)")
            perm_btn.setObjectName("dangerBtn")
            perm_btn.clicked.connect(self._permanent_delete)
            action_row.addWidget(perm_btn)
        layout.addLayout(action_row)

        self.refresh()

    def refresh(self) -> None:
        rows = category_service.list_categories(include_deleted=True)
        body = [
            [
                str(r["category_id"]),
                r["category_name"],
                str(r["product_count"]),
                "Deleted" if r["is_deleted"] else "Active",
                "",
            ]
            for r in rows
        ]
        self.table.set_rows(body)

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())

    def _add(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Category", "Name:")
        if not ok:
            return
        err = V.text_length(name, "Category name", minimum=2, maximum=50)
        if err:
            QMessageBox.warning(self, "Invalid name", err)
            return
        try:
            category_service.add_category(name.strip())
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _edit_selected(self) -> None:
        cid = self._selected_id()
        if cid is None:
            return
        current = self.table.item(self.table.currentRow(), 1).text()
        name, ok = QInputDialog.getText(self, "Edit Category", "Name:", text=current)
        if not ok:
            return
        err = V.text_length(name, "Category name", minimum=2, maximum=50)
        if err:
            QMessageBox.warning(self, "Invalid name", err)
            return
        category_service.update_category(cid, name.strip())
        self.refresh()

    def _delete_selected(self) -> None:
        cid = self._selected_id()
        if cid is None:
            return
        if QMessageBox.question(self, "Confirm", "Soft-delete this category?") == QMessageBox.StandardButton.Yes:
            category_service.soft_delete_category(cid)
            self.refresh()

    def _recover_selected(self) -> None:
        cid = self._selected_id()
        if cid is None:
            return
        category_service.recover_category(cid)
        self.refresh()

    def _permanent_delete(self) -> None:
        cid = self._selected_id()
        if cid is None:
            return
        name = self.table.item(self.table.currentRow(), 1).text()
        confirm = QMessageBox.warning(
            self, "Permanent Delete",
            f"Permanently delete category '{name}'?\n\n"
            "This cannot be undone. The category must have no products "
            "assigned to it.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            category_service.permanent_delete_category(cid)
        except ValueError as e:
            QMessageBox.warning(self, "Cannot delete", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.refresh()
