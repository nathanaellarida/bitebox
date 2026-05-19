"""Staff management tab (Admin only)."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget
)

from gui.widgets.data_table import DataTable
from gui.widgets import validators as V
from models.staff import StaffModel
from services import staff_service


class StaffEditor(QDialog):
    def __init__(self, parent=None, data: dict | None = None):
        super().__init__(parent)
        self.is_edit = data is not None
        self.setWindowTitle("Edit Staff" if self.is_edit else "Add Staff")
        self.setMinimumWidth(420)

        self.first = QLineEdit()
        self.last = QLineEdit()
        self.email = QLineEdit()
        self.role = QComboBox()
        self.role.addItems(["Staff", "Admin"])
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.is_active = QCheckBox("Active")
        self.is_active.setChecked(True)

        if data:
            self.first.setText(data.get("first_name", ""))
            self.last.setText(data.get("last_name", ""))
            self.email.setText(data.get("email", ""))
            self.role.setCurrentText(data.get("role", "Staff"))
            self.is_active.setChecked(bool(data.get("is_active", True)))

        form = QFormLayout()
        form.addRow("First Name *", self.first)
        form.addRow("Last Name *", self.last)
        form.addRow("Email *", self.email)
        form.addRow("Role", self.role)
        if not self.is_edit:
            form.addRow("Password *", self.password)
        form.addRow(self.is_active)

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
        root.addLayout(btns)
        V.install_error_qss(self)

    def _save(self):
        V.clear_errors([self.first, self.last, self.email, self.password])
        errors: list[tuple[object, str]] = []
        e = V.name(self.first.text(), "First name");  errors.append((self.first, e)) if e else None
        e = V.name(self.last.text(), "Last name");  errors.append((self.last, e)) if e else None
        e = V.email(self.email.text());  errors.append((self.email, e)) if e else None
        if not self.is_edit:
            e = V.password_strength(self.password.text())
            if e: errors.append((self.password, e))
        if errors:
            for widget, _ in errors:
                V.mark_error(widget, True)
            QMessageBox.warning(self, "Check the form", errors[0][1])
            return
        self.accept()

    def values(self) -> dict:
        return {
            "first_name": self.first.text().strip(),
            "last_name": self.last.text().strip(),
            "email": self.email.text().strip(),
            "role": self.role.currentText(),
            "password": self.password.text(),
            "is_active": self.is_active.isChecked(),
        }


class StaffTab(QWidget):
    HEADERS = ["ID", "Full Name", "Email", "Role", "Status", "Last Login"]

    def __init__(self, current_staff: StaffModel, parent=None):
        super().__init__(parent)
        self.current_staff = current_staff

        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        add = QPushButton("+ Add Staff")
        add.setObjectName("primaryBtn")
        add.clicked.connect(self._add)
        bar.addWidget(add)
        bar.addStretch(1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        bar.addWidget(refresh)
        layout.addLayout(bar)

        self.table = DataTable(self.HEADERS)
        self.table.cellDoubleClicked.connect(self._edit)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._edit)
        reset_btn = QPushButton("Reset Password")
        reset_btn.clicked.connect(self._reset)
        del_btn = QPushButton("Delete")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._delete)
        actions.addStretch(1)
        actions.addWidget(edit_btn)
        actions.addWidget(reset_btn)
        actions.addWidget(del_btn)
        layout.addLayout(actions)
        self.refresh()

    def refresh(self) -> None:
        rows = staff_service.list_staff()
        body = [
            [
                str(s.staff_id), s.full_name, s.email, s.role,
                "Active" if s.is_active else "Inactive",
                s.last_login.strftime("%Y-%m-%d %H:%M") if s.last_login else "—",
            ]
            for s in rows
        ]
        self.table.set_rows(body)

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())

    def _add(self) -> None:
        dlg = StaffEditor(self)
        if dlg.exec():
            v = dlg.values()
            try:
                staff_service.add_staff(v["first_name"], v["last_name"], v["email"], v["role"], v["password"])
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _edit(self) -> None:
        sid = self._selected_id()
        if sid is None:
            return
        rows = {s.staff_id: s for s in staff_service.list_staff()}
        s = rows.get(sid)
        if not s:
            return
        dlg = StaffEditor(self, {
            "first_name": s.first_name, "last_name": s.last_name, "email": s.email,
            "role": s.role, "is_active": s.is_active,
        })
        if dlg.exec():
            v = dlg.values()
            try:
                staff_service.update_staff(sid, v["first_name"], v["last_name"], v["email"], v["role"], v["is_active"])
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _reset(self) -> None:
        sid = self._selected_id()
        if sid is None:
            return
        new_pw = staff_service.reset_password(sid)
        QMessageBox.information(self, "Password Reset", f"Temporary password:\n\n{new_pw}\n\nShare it with the staff member.")

    def _delete(self) -> None:
        sid = self._selected_id()
        if sid is None:
            return
        if sid == self.current_staff.staff_id:
            QMessageBox.warning(self, "Not Allowed", "You cannot delete yourself.")
            return
        if QMessageBox.question(self, "Confirm", "Delete this staff?") == QMessageBox.StandardButton.Yes:
            staff_service.delete_staff(sid)
            self.refresh()
