"""Settings tab — store info, SMTP config, theme."""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget
)

from config import load_config, save_config
from gui.widgets import validators as V
from services import email_service


class SettingsTab(QWidget):
    theme_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cfg = load_config()
        layout = QVBoxLayout(self)

        # Store
        store_box = QGroupBox("Store Information")
        sf = QFormLayout(store_box)
        self.store_name = QLineEdit(self.cfg["store"].get("name", ""))
        self.store_contact = QLineEdit(self.cfg["store"].get("contact", ""))
        self.store_email = QLineEdit(self.cfg["store"].get("email", ""))
        self.store_address = QLineEdit(self.cfg["store"].get("address", ""))
        sf.addRow("Name", self.store_name)
        sf.addRow("Contact", self.store_contact)
        sf.addRow("Email", self.store_email)
        sf.addRow("Address", self.store_address)
        layout.addWidget(store_box)

        # SMTP
        smtp_box = QGroupBox("SMTP Email Configuration")
        smtp_form = QFormLayout(smtp_box)
        smtp = self.cfg.get("smtp", {})
        self.host = QLineEdit(smtp.get("host", ""))
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(int(smtp.get("port", 587)))
        self.username = QLineEdit(smtp.get("username", ""))
        self.password = QLineEdit(smtp.get("password", ""))
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.use_tls = QCheckBox("Use TLS")
        self.use_tls.setChecked(bool(smtp.get("use_tls", True)))
        self.from_name = QLineEdit(smtp.get("from_name", ""))
        smtp_form.addRow("Host", self.host)
        smtp_form.addRow("Port", self.port)
        smtp_form.addRow("Username", self.username)
        smtp_form.addRow("Password", self.password)
        smtp_form.addRow("From Name", self.from_name)
        smtp_form.addRow(self.use_tls)

        test_btn = QPushButton("Send Test Email")
        test_btn.clicked.connect(self._test_email)
        smtp_form.addRow(test_btn)
        layout.addWidget(smtp_box)

        # Theme
        theme_box = QGroupBox("Appearance")
        tf = QFormLayout(theme_box)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        self.theme_combo.setCurrentText(self.cfg.get("theme", "light"))
        tf.addRow("Theme", self.theme_combo)
        layout.addWidget(theme_box)

        # Save / Reset
        action_row = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save)
        action_row.addStretch(1)
        action_row.addWidget(save_btn)
        layout.addLayout(action_row)
        layout.addStretch(1)
        V.install_error_qss(self)

    def refresh(self) -> None:
        pass

    def _validate(self) -> str | None:
        """Return the first validation failure, or None if everything is OK."""
        V.clear_errors([
            self.store_name, self.store_contact, self.store_email,
            self.store_address, self.host, self.username, self.password,
            self.from_name,
        ])
        errors: list[tuple[object, str]] = []
        e = V.text_length(self.store_name.text(), "Store name",
                          minimum=2, maximum=80)
        if e: errors.append((self.store_name, e))
        e = V.phone(self.store_contact.text(), "Store contact",
                    optional=True)
        if e: errors.append((self.store_contact, e))
        if self.store_email.text().strip():
            e = V.email(self.store_email.text(), "Store email")
            if e: errors.append((self.store_email, e))
        if len(self.store_address.text().strip()) > 200:
            errors.append((self.store_address,
                           "Store address must be at most 200 characters."))

        # SMTP fields are only validated when at least one is filled.
        smtp_filled = any(w.text().strip() for w in
                          (self.host, self.username, self.password,
                           self.from_name))
        if smtp_filled:
            e = V.required(self.host.text(), "SMTP host")
            if e: errors.append((self.host, e))
            e = V.required(self.username.text(), "SMTP username")
            if e: errors.append((self.username, e))
            e = V.required(self.password.text(), "SMTP password")
            if e: errors.append((self.password, e))
            if self.username.text().strip():
                e = V.email(self.username.text(), "SMTP username")
                if e: errors.append((self.username, e))

        if errors:
            for widget, _ in errors:
                V.mark_error(widget, True)
            return errors[0][1]
        return None

    def _save(self) -> None:
        err = self._validate()
        if err:
            QMessageBox.warning(self, "Check the form", err)
            return
        self.cfg["store"] = {
            "name": self.store_name.text().strip(),
            "contact": self.store_contact.text().strip(),
            "email": self.store_email.text().strip(),
            "address": self.store_address.text().strip(),
        }
        self.cfg["smtp"] = {
            "host": self.host.text().strip(),
            "port": self.port.value(),
            "username": self.username.text().strip(),
            "password": self.password.text(),
            "use_tls": self.use_tls.isChecked(),
            "from_name": self.from_name.text().strip(),
        }
        new_theme = self.theme_combo.currentText()
        theme_changed = new_theme != self.cfg.get("theme")
        self.cfg["theme"] = new_theme
        save_config(self.cfg)
        QMessageBox.information(self, "Saved", "Settings saved.")
        if theme_changed:
            self.theme_changed.emit()

    def _test_email(self) -> None:
        # save SMTP first so the email service can read latest values
        self._save()
        ok, msg = email_service.send_test_email()
        (QMessageBox.information if ok else QMessageBox.critical)(self, "Test Email", msg)
