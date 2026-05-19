"""Customer 'Profile' tab — edit account info + structured delivery
address + change password. Saved address fields auto-fill checkout."""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget
)

from models.customer import CustomerModel
from gui.widgets import validators as V
from services import customer_auth_service, customer_service


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "font-size:15px;font-weight:800;color:#111827;"
        "background:transparent;padding:0;margin:0;"
    )
    return lbl


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color:#374151;font-weight:600;font-size:12px;"
        "background:transparent;padding:0;"
    )
    return lbl


def _styled_input() -> QLineEdit:
    e = QLineEdit()
    e.setMinimumHeight(40)
    return e


def _row(label: str, widget) -> QVBoxLayout:
    box = QVBoxLayout()
    box.setSpacing(6)
    box.addWidget(_field_label(label))
    if isinstance(widget, QLayout := type(widget).__mro__[0]):  # noqa: F841
        pass
    if hasattr(widget, "addWidget"):  # already a layout
        box.addLayout(widget)
    else:
        box.addWidget(widget)
    return box


class ProfileTab(QWidget):
    profile_updated = pyqtSignal(object)  # CustomerModel

    def __init__(self, customer: CustomerModel, parent=None):
        super().__init__(parent)
        self.customer = customer

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(20)
        V.install_error_qss(self)

        title = QLabel("Profile")
        title.setStyleSheet(
            "font-size:24px;font-weight:800;color:#111827;background:transparent;"
        )
        sub = QLabel("Manage your account information and password.")
        sub.setStyleSheet("color:#6B7280;font-size:13px;background:transparent;")
        v.addWidget(title)
        v.addWidget(sub)

        # ---- Account Info card ----
        info_card = QFrame()
        info_card.setObjectName("card")
        info_l = QVBoxLayout(info_card)
        info_l.setContentsMargins(28, 24, 28, 24)
        info_l.setSpacing(18)
        info_l.addWidget(_section_title("Account Information"))

        # Email — plain read-only label, no card / pill background
        email_block = QVBoxLayout()
        email_block.setSpacing(2)
        email_block.addWidget(_field_label("Email (cannot be changed)"))
        email_display = QLabel(customer.email)
        email_display.setStyleSheet(
            "color:#111827;font-size:14px;background:transparent;"
            "padding:6px 0;"
        )
        email_display.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        email_block.addWidget(email_display)
        info_l.addLayout(email_block)

        # First / Last name side-by-side
        names_row = QHBoxLayout()
        names_row.setSpacing(20)

        first_box = QVBoxLayout(); first_box.setSpacing(6)
        first_box.addWidget(_field_label("First Name"))
        self.first = _styled_input()
        self.first.setText(customer.first_name)
        first_box.addWidget(self.first)
        names_row.addLayout(first_box, 1)

        last_box = QVBoxLayout(); last_box.setSpacing(6)
        last_box.addWidget(_field_label("Last Name"))
        self.last = _styled_input()
        self.last.setText(customer.last_name)
        last_box.addWidget(self.last)
        names_row.addLayout(last_box, 1)
        info_l.addLayout(names_row)

        # Contact
        contact_box = QVBoxLayout(); contact_box.setSpacing(6)
        contact_box.addWidget(_field_label("Contact Number"))
        self.contact = _styled_input()
        self.contact.setPlaceholderText("e.g. 0917-555-1234")
        self.contact.setText(customer.contact_number or "")
        contact_box.addWidget(self.contact)
        info_l.addLayout(contact_box)

        info_l.addWidget(_section_title("Delivery Address"))
        hint = QLabel(
            "Saved here so it auto-fills when you order with delivery."
        )
        hint.setStyleSheet("color:#6B7280;font-size:12px;background:transparent;")
        info_l.addWidget(hint)

        street_box = QVBoxLayout(); street_box.setSpacing(6)
        street_box.addWidget(_field_label("Street, building, unit"))
        self.street = _styled_input()
        self.street.setPlaceholderText("e.g. 123 Mango St., Unit 4B")
        self.street.setText(customer.street or "")
        street_box.addWidget(self.street)
        info_l.addLayout(street_box)

        # City / Province / Postal code on one row
        cpp_row = QHBoxLayout()
        cpp_row.setSpacing(14)

        city_box = QVBoxLayout(); city_box.setSpacing(6)
        city_box.addWidget(_field_label("City"))
        self.city = _styled_input()
        self.city.setText(customer.city or "")
        city_box.addWidget(self.city)
        cpp_row.addLayout(city_box, 2)

        province_box = QVBoxLayout(); province_box.setSpacing(6)
        province_box.addWidget(_field_label("Province / State"))
        self.province = _styled_input()
        self.province.setText(customer.province or "")
        province_box.addWidget(self.province)
        cpp_row.addLayout(province_box, 2)

        postal_box = QVBoxLayout(); postal_box.setSpacing(6)
        postal_box.addWidget(_field_label("Postal code"))
        self.postal = _styled_input()
        self.postal.setMaxLength(10)
        self.postal.setText(customer.postal_code or "")
        postal_box.addWidget(self.postal)
        cpp_row.addLayout(postal_box, 1)
        info_l.addLayout(cpp_row)

        landmark_box = QVBoxLayout(); landmark_box.setSpacing(6)
        landmark_box.addWidget(_field_label("Landmark or notes (optional)"))
        self.landmark = _styled_input()
        self.landmark.setPlaceholderText("Near the bakery / Gate 2 / etc.")
        self.landmark.setText(customer.landmark or "")
        landmark_box.addWidget(self.landmark)
        info_l.addLayout(landmark_box)

        info_l.addSpacing(4)
        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumHeight(42)
        save_btn.setMinimumWidth(160)
        save_btn.clicked.connect(self._save_profile)
        save_row.addWidget(save_btn)
        info_l.addLayout(save_row)
        v.addWidget(info_card)

        # ---- Change password card ----
        pw_card = QFrame()
        pw_card.setObjectName("card")
        pw_l = QVBoxLayout(pw_card)
        pw_l.setContentsMargins(28, 24, 28, 24)
        pw_l.setSpacing(18)
        pw_l.addWidget(_section_title("Change Password"))

        password_hint = QLabel(
            "Use at least 8 characters with one uppercase letter and one digit."
        )
        password_hint.setStyleSheet("color:#6B7280;font-size:12px;background:transparent;")
        pw_l.addWidget(password_hint)

        cur_box = QVBoxLayout(); cur_box.setSpacing(6)
        cur_box.addWidget(_field_label("Current Password"))
        self.cur_pw = _styled_input(); self.cur_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.cur_pw.setPlaceholderText("Enter your current password")
        cur_box.addWidget(self.cur_pw)
        pw_l.addLayout(cur_box)

        new_pw_row = QHBoxLayout()
        new_pw_row.setSpacing(20)
        new_box = QVBoxLayout(); new_box.setSpacing(6)
        new_box.addWidget(_field_label("New Password"))
        self.new_pw = _styled_input(); self.new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        new_box.addWidget(self.new_pw)
        new_pw_row.addLayout(new_box, 1)

        new2_box = QVBoxLayout(); new2_box.setSpacing(6)
        new2_box.addWidget(_field_label("Confirm New Password"))
        self.new_pw2 = _styled_input(); self.new_pw2.setEchoMode(QLineEdit.EchoMode.Password)
        new2_box.addWidget(self.new_pw2)
        new_pw_row.addLayout(new2_box, 1)
        pw_l.addLayout(new_pw_row)

        pw_action = QHBoxLayout()
        self.pw_msg = QLabel("")
        self.pw_msg.setStyleSheet("font-size:12px;background:transparent;")
        pw_action.addWidget(self.pw_msg, 1)
        pw_btn = QPushButton("Update Password")
        pw_btn.setObjectName("primaryBtn")
        pw_btn.setMinimumHeight(42)
        pw_btn.setMinimumWidth(180)
        pw_btn.clicked.connect(self._change_pw)
        pw_action.addWidget(pw_btn)
        pw_l.addLayout(pw_action)

        v.addWidget(pw_card)
        v.addStretch(1)

    def refresh(self) -> None:
        c = customer_service.get_customer(self.customer.customer_id)
        if c:
            self.customer = c
            self.first.setText(c.first_name)
            self.last.setText(c.last_name)
            self.contact.setText(c.contact_number or "")
            self.street.setText(c.street or "")
            self.city.setText(c.city or "")
            self.province.setText(c.province or "")
            self.postal.setText(c.postal_code or "")
            self.landmark.setText(c.landmark or "")

    def _save_profile(self) -> None:
        fields = [self.first, self.last, self.contact, self.street,
                  self.city, self.province, self.postal, self.landmark]
        V.clear_errors(fields)

        # All structured-address fields are optional individually, but if the
        # customer fills *any* of street/city/province/postal we treat the
        # whole block as "they're entering a delivery address" and require
        # the four required fields, mirroring the checkout dialog.
        any_address = any(w.text().strip() for w in
                          (self.street, self.city, self.province, self.postal))

        errors: list[tuple[object, str]] = []
        e = V.name(self.first.text(), "First name");  errors.append((self.first, e)) if e else None
        e = V.name(self.last.text(), "Last name");  errors.append((self.last, e)) if e else None
        e = V.phone(self.contact.text(), optional=True)
        if e: errors.append((self.contact, e))

        if any_address:
            e = V.required(self.street.text(), "Street");  errors.append((self.street, e)) if e else None
            e = V.required(self.city.text(), "City");  errors.append((self.city, e)) if e else None
            e = V.required(self.province.text(), "Province");  errors.append((self.province, e)) if e else None
            e = V.postal_code(self.postal.text());  errors.append((self.postal, e)) if e else None
        else:
            e = V.postal_code(self.postal.text(), optional=True)
            if e: errors.append((self.postal, e))

        if self.landmark.text().strip() and len(self.landmark.text().strip()) > 120:
            errors.append((self.landmark, "Landmark must be at most 120 characters."))

        if errors:
            for widget, _ in errors:
                V.mark_error(widget, True)
            QMessageBox.warning(self, "Check the form", errors[0][1])
            return

        try:
            customer_service.update_profile(
                self.customer.customer_id,
                self.first.text(), self.last.text(),
                contact_number=self.contact.text(),
                # Keep legacy free-form `address` in sync with the structured
                # fields so older data isn't lost.
                address=self._compose_legacy_address(),
                street=self.street.text(),
                city=self.city.text(),
                province=self.province.text(),
                postal_code=self.postal.text(),
                landmark=self.landmark.text(),
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        c = customer_service.get_customer(self.customer.customer_id)
        if c:
            self.customer = c
            self.profile_updated.emit(c)
        QMessageBox.information(self, "Saved", "Profile updated.")

    def _compose_legacy_address(self) -> str:
        parts = [self.street.text().strip(), self.city.text().strip(),
                 self.province.text().strip(), self.postal.text().strip()]
        line = ", ".join(p for p in parts if p)
        landmark = self.landmark.text().strip()
        if landmark:
            line = f"{line} ({landmark})" if line else landmark
        return line

    def _change_pw(self) -> None:
        cur, new, new2 = self.cur_pw.text(), self.new_pw.text(), self.new_pw2.text()
        V.clear_errors([self.cur_pw, self.new_pw, self.new_pw2])

        errors: list[tuple[object, str]] = []
        e = V.required(cur, "Current password")
        if e: errors.append((self.cur_pw, e))
        e = V.password_strength(new, "New password")
        if e: errors.append((self.new_pw, e))
        e = V.passwords_match(new, new2)
        if e: errors.append((self.new_pw2, e))
        if cur and new and cur == new:
            errors.append((self.new_pw, "New password must differ from the current one."))

        if errors:
            for widget, _ in errors:
                V.mark_error(widget, True)
            self._set_pw_msg(errors[0][1], "#EF4444")
            return

        err = customer_auth_service.change_password(self.customer.customer_id, cur, new)
        if err:
            V.mark_error(self.cur_pw, True)
            self._set_pw_msg(err, "#EF4444")
            return
        self.cur_pw.clear(); self.new_pw.clear(); self.new_pw2.clear()
        self._set_pw_msg("Password updated.", "#10B981")

    def _set_pw_msg(self, msg: str, color: str) -> None:
        self.pw_msg.setText(msg)
        self.pw_msg.setStyleSheet(
            f"color:{color};font-size:12px;font-weight:600;background:transparent;"
        )
