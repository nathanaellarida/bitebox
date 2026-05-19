"""Unified portal login + register window.

Sign In tries staff authentication first; if that fails it falls back
to customer authentication. Whichever succeeds determines which portal
opens (admin vs. customer).
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QStackedWidget, QToolButton, QVBoxLayout, QWidget
)

from config import load_config
from gui.widgets import validators as V
from models.customer import CustomerModel
from models.staff import StaffModel
from services import auth_service, customer_auth_service


class _PasswordField(QFrame):
    """Password input with reveal toggle, used for login + register."""

    FIELD_HEIGHT = 40

    def __init__(self, placeholder: str, parent=None):
        super().__init__(parent)
        # The wrapper itself stays transparent so it picks up the page bg.
        self.setStyleSheet("QFrame{background:transparent;border:none;}")
        self.setFixedHeight(self.FIELD_HEIGHT)
        l = QHBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setFixedHeight(self.FIELD_HEIGHT)
        # Square off the right edge so the reveal button can sit flush.
        self.edit.setStyleSheet(
            "QLineEdit{border-top-right-radius:0;border-bottom-right-radius:0;"
            "border-right:none;}"
        )
        self.toggle = QToolButton()
        self.toggle.setText("\U0001F441")  # 👁
        self.toggle.setCheckable(True)
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.setFixedSize(40, self.FIELD_HEIGHT)
        # Match the line-edit's border so the seam is invisible, and
        # vertically center the glyph by removing extra padding.
        self.toggle.setStyleSheet(
            "QToolButton{border:1.5px solid #D1D5DB;border-left:none;"
            "border-top-right-radius:8px;border-bottom-right-radius:8px;"
            "background:#fff;padding:0;margin:0;}"
            "QToolButton:checked{background:#EEF2FF;}"
            "QToolButton:hover{background:#F3F4F6;}"
        )
        self.toggle.toggled.connect(
            lambda on: self.edit.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
            )
        )
        l.addWidget(self.edit, 1)
        l.addWidget(self.toggle)

    def text(self) -> str:
        return self.edit.text()

    def clear(self) -> None:
        self.edit.clear()


class CustomerLoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign In")
        self.setFixedSize(880, 580)
        self.customer: CustomerModel | None = None
        self.staff: StaffModel | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_branding(), 4)
        root.addWidget(self._build_forms(), 6)
        V.install_error_qss(self)

    def _build_branding(self) -> QWidget:
        from gui.customer.branding_panel import BrandingPanel
        panel = BrandingPanel("branding_image.jpg")
        v = QVBoxLayout(panel)
        v.setContentsMargins(40, 40, 40, 40)
        v.addStretch(1)
        store_name = load_config().get("store", {}).get("name", "Our Store")
        title = QLabel(store_name)
        title.setObjectName("brandingTitle")
        title.setWordWrap(True)
        v.addWidget(title)
        tagline = QLabel("Order your favorites,\nanytime.")
        tagline.setObjectName("brandingTagline")
        tagline.setWordWrap(True)
        v.addWidget(tagline)
        v.addSpacing(40)
        for txt in ("✓ Browse our menu in real time",
                    "✓ Track every order from your dashboard",
                    "✓ Apply promo codes at checkout"):
            lbl = QLabel(txt)
            lbl.setObjectName("brandingBullet")
            v.addWidget(lbl)
        v.addStretch(2)
        footer = QLabel("Secure customer portal")
        footer.setObjectName("brandingFooter")
        v.addWidget(footer)
        return panel

    def _build_forms(self) -> QWidget:
        wrap = QFrame()
        wrap.setObjectName("formsWrap")
        # Paint the wrapper AND every plain QWidget / QStackedWidget descendant
        # so the right-hand panel is uniformly white. Without this, the global
        # `QWidget { background:#F9FAFB }` rule bleeds through onto child
        # pages and produces a grey block behind the heading.
        wrap.setStyleSheet(
            "QFrame#formsWrap, QFrame#formsWrap > QWidget,"
            " QFrame#formsWrap QStackedWidget,"
            " QFrame#formsWrap QStackedWidget > QWidget"
            " { background:#FFFFFF; }"
        )
        v = QVBoxLayout(wrap)
        v.setContentsMargins(48, 36, 48, 36)
        v.setSpacing(8)

        # Tab switcher
        tab_row = QHBoxLayout()
        self.btn_login = QPushButton("Sign In")
        self.btn_register = QPushButton("Create Account")
        for b in (self.btn_login, self.btn_register):
            b.setObjectName("navTabBtn")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setChecked(True)
        self.btn_login.clicked.connect(lambda: self._switch(0))
        self.btn_register.clicked.connect(lambda: self._switch(1))
        tab_row.addWidget(self.btn_login)
        tab_row.addWidget(self.btn_register)
        tab_row.addStretch(1)
        v.addLayout(tab_row)

        v.addSpacing(20)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_login_page())
        self.stack.addWidget(self._build_register_page())
        v.addWidget(self.stack, 1)
        return wrap

    def _switch(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)
        self.btn_login.setChecked(idx == 0)
        self.btn_register.setChecked(idx == 1)

    # ---------- LOGIN ----------
    def _build_login_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        title = QLabel("Welcome back")
        title.setStyleSheet("font-size:22px;font-weight:800;background:transparent;")
        sub = QLabel("Enter your account details below")
        sub.setStyleSheet("color:#6B7280;background:transparent;")
        v.addWidget(title)
        v.addWidget(sub)
        v.addSpacing(14)

        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("Email address")
        self.login_email.setMinimumHeight(38)
        v.addWidget(self.login_email)

        self.login_pw = _PasswordField("Password")
        v.addWidget(self.login_pw)

        self.login_msg = QLabel("")
        self.login_msg.setStyleSheet("color:#EF4444;font-size:12px;background:transparent;")
        self.login_msg.setVisible(False)
        v.addWidget(self.login_msg)

        sign_in_btn = QPushButton("Sign In")
        sign_in_btn.setObjectName("primaryBtn")
        sign_in_btn.setMinimumHeight(44)
        sign_in_btn.clicked.connect(self._do_login)
        v.addWidget(sign_in_btn)

        no_acc = QLabel("New here? <a href='#'>Create an account</a>")
        no_acc.setOpenExternalLinks(False)
        no_acc.setStyleSheet("color:#6B7280;font-size:12px;background:transparent;")
        no_acc.linkActivated.connect(lambda *_: self._switch(1))
        v.addWidget(no_acc)

        # Seed credentials hint so a fresh install can sign in to either portal.
        admin_hint = QLabel(
            "<div style='line-height:1.5'>"
            "<span style='color:#9CA3AF'>Admin: </span>"
            "<span style='color:#1E1B4B;font-weight:600'>admin@store.com</span>"
            "<span style='color:#9CA3AF'> &nbsp;·&nbsp; </span>"
            "<span style='color:#1E1B4B;font-weight:600'>Admin@1234</span><br>"
            "<span style='color:#9CA3AF'>Customer: </span>"
            "<span style='color:#1E1B4B;font-weight:600'>juan@example.com</span>"
            "<span style='color:#9CA3AF'> &nbsp;·&nbsp; </span>"
            "<span style='color:#1E1B4B;font-weight:600'>Customer@1234</span>"
            "</div>"
        )
        admin_hint.setStyleSheet("font-size:11px;margin-top:14px;background:transparent;")
        admin_hint.setTextFormat(Qt.TextFormat.RichText)
        v.addWidget(admin_hint)

        v.addStretch(1)
        return page

    def _do_login(self) -> None:
        email = self.login_email.text().strip()
        pw = self.login_pw.text()
        self.login_msg.setVisible(False)
        V.clear_errors([self.login_email, self.login_pw.edit])

        # Lightweight format checks before hitting the DB.
        err = V.first_error(
            V.email(email),
            V.required(pw, "Password"),
        )
        if err:
            if not email:
                V.mark_error(self.login_email, True)
            elif not V.EMAIL_RE.match(email):
                V.mark_error(self.login_email, True)
            if not pw:
                V.mark_error(self.login_pw.edit, True)
            self._show_login_error(err)
            return

        # Try staff first; on failure, fall back to customer.
        s = auth_service.login(email, pw)
        if s:
            self.staff = s
            self.accept()
            return
        c = customer_auth_service.login(email, pw)
        if c:
            self.customer = c
            self.accept()
            return
        V.mark_error(self.login_email, True)
        V.mark_error(self.login_pw.edit, True)
        self._show_login_error("Invalid credentials or inactive account.")

    def _show_login_error(self, msg: str) -> None:
        self.login_msg.setText(msg)
        self.login_msg.setStyleSheet("color:#EF4444;font-size:12px;background:transparent;")
        self.login_msg.setVisible(True)

    # ---------- REGISTER ----------
    def _build_register_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        title = QLabel("Create your account")
        title.setStyleSheet("font-size:22px;font-weight:800;background:transparent;")
        sub = QLabel("It only takes a minute.")
        sub.setStyleSheet("color:#6B7280;background:transparent;")
        v.addWidget(title)
        v.addWidget(sub)
        v.addSpacing(8)

        name_row = QHBoxLayout()
        self.reg_first = QLineEdit(); self.reg_first.setPlaceholderText("First name")
        self.reg_last = QLineEdit(); self.reg_last.setPlaceholderText("Last name")
        for w in (self.reg_first, self.reg_last):
            w.setMinimumHeight(36)
            name_row.addWidget(w)
        v.addLayout(name_row)

        self.reg_email = QLineEdit(); self.reg_email.setPlaceholderText("Email")
        self.reg_email.setMinimumHeight(36)
        v.addWidget(self.reg_email)

        self.reg_contact = QLineEdit(); self.reg_contact.setPlaceholderText("Contact number (optional)")
        self.reg_contact.setMinimumHeight(36)
        v.addWidget(self.reg_contact)

        self.reg_pw = _PasswordField("Password (min 8 chars, 1 uppercase, 1 digit)")
        self.reg_pw_confirm = _PasswordField("Confirm password")
        v.addWidget(self.reg_pw)
        v.addWidget(self.reg_pw_confirm)

        # Structured delivery address — same layout as the profile tab and
        # the checkout dialog. All fields are optional at registration; the
        # validator only enforces the four required ones if the user starts
        # filling any of them in.
        addr_section = QLabel("Delivery address (optional)")
        addr_section.setStyleSheet(
            "font-size:13px;font-weight:700;color:#374151;"
            "background:transparent;padding-top:6px;"
        )
        v.addWidget(addr_section)

        addr_hint = QLabel(
            "Saved here so it auto-fills when you order with delivery."
        )
        addr_hint.setStyleSheet(
            "color:#6B7280;font-size:11px;background:transparent;"
        )
        v.addWidget(addr_hint)

        self.reg_street = QLineEdit()
        self.reg_street.setPlaceholderText("Street, building, unit (e.g. 123 Mango St., Unit 4B)")
        self.reg_street.setMinimumHeight(36)
        v.addWidget(self.reg_street)

        cpp_row = QHBoxLayout()
        cpp_row.setSpacing(10)
        self.reg_city = QLineEdit(); self.reg_city.setPlaceholderText("City")
        self.reg_province = QLineEdit(); self.reg_province.setPlaceholderText("Province / State")
        self.reg_postal = QLineEdit(); self.reg_postal.setPlaceholderText("Postal code")
        self.reg_postal.setMaxLength(10)
        for w in (self.reg_city, self.reg_province, self.reg_postal):
            w.setMinimumHeight(36)
        cpp_row.addWidget(self.reg_city, 2)
        cpp_row.addWidget(self.reg_province, 2)
        cpp_row.addWidget(self.reg_postal, 1)
        v.addLayout(cpp_row)

        self.reg_landmark = QLineEdit()
        self.reg_landmark.setPlaceholderText("Landmark or notes (optional)")
        self.reg_landmark.setMinimumHeight(36)
        v.addWidget(self.reg_landmark)

        self.reg_msg = QLabel("")
        self.reg_msg.setStyleSheet("color:#EF4444;font-size:12px;background:transparent;")
        self.reg_msg.setVisible(False)
        v.addWidget(self.reg_msg)

        create_btn = QPushButton("Create Account")
        create_btn.setObjectName("primaryBtn")
        create_btn.setMinimumHeight(44)
        create_btn.clicked.connect(self._do_register)
        v.addWidget(create_btn)
        v.addStretch(1)
        return page

    def _do_register(self) -> None:
        self.reg_msg.setVisible(False)
        fields = [self.reg_first, self.reg_last, self.reg_email,
                  self.reg_contact, self.reg_pw.edit,
                  self.reg_pw_confirm.edit, self.reg_street,
                  self.reg_city, self.reg_province, self.reg_postal,
                  self.reg_landmark]
        V.clear_errors(fields)

        first, last = self.reg_first.text(), self.reg_last.text()
        email = self.reg_email.text().strip()
        contact = self.reg_contact.text().strip()
        pw, pw2 = self.reg_pw.text(), self.reg_pw_confirm.text()
        street = self.reg_street.text().strip()
        city = self.reg_city.text().strip()
        province = self.reg_province.text().strip()
        postal = self.reg_postal.text().strip()
        landmark = self.reg_landmark.text().strip()

        # Run all validators and show the first failure inline. Mark every
        # offending field so the user can spot them at a glance.
        errors: list[tuple[object, str]] = []
        e = V.name(first, "First name"); errors.append((self.reg_first, e)) if e else None
        e = V.name(last, "Last name"); errors.append((self.reg_last, e)) if e else None
        e = V.email(email); errors.append((self.reg_email, e)) if e else None
        e = V.phone(contact, optional=True); errors.append((self.reg_contact, e)) if e else None
        e = V.password_strength(pw); errors.append((self.reg_pw.edit, e)) if e else None
        e = V.passwords_match(pw, pw2)
        if e:
            errors.append((self.reg_pw_confirm.edit, e))

        # Address: same conditional rule the profile tab uses. If the user
        # touched any address line, all four required fields must be filled.
        any_address = any((street, city, province, postal))
        if any_address:
            e = V.required(street, "Street"); errors.append((self.reg_street, e)) if e else None
            e = V.required(city, "City"); errors.append((self.reg_city, e)) if e else None
            e = V.required(province, "Province"); errors.append((self.reg_province, e)) if e else None
            e = V.postal_code(postal); errors.append((self.reg_postal, e)) if e else None
        else:
            e = V.postal_code(postal, optional=True)
            if e: errors.append((self.reg_postal, e))
        if landmark and len(landmark) > 120:
            errors.append((self.reg_landmark, "Landmark must be at most 120 characters."))

        if errors:
            for widget, _ in errors:
                V.mark_error(widget, True)
            self._show_reg(errors[0][1], "#EF4444")
            return

        result = customer_auth_service.register(
            first, last, email, pw,
            contact_number=contact,
            street=street, city=city, province=province,
            postal_code=postal, landmark=landmark,
        )
        if isinstance(result, str):
            self._show_reg(result, "#EF4444")
            return

        # success: auto-switch to login, prefill email, show green message
        self.reg_first.clear(); self.reg_last.clear()
        self.reg_email.clear(); self.reg_contact.clear()
        self.reg_pw.clear(); self.reg_pw_confirm.clear()
        self.reg_street.clear(); self.reg_city.clear()
        self.reg_province.clear(); self.reg_postal.clear()
        self.reg_landmark.clear()
        self._switch(0)
        self.login_email.setText(result.email)
        self.login_msg.setText("Account created — please sign in.")
        self.login_msg.setStyleSheet("color:#10B981;font-size:12px;font-weight:600;background:transparent;")
        self.login_msg.setVisible(True)

    def _show_reg(self, msg: str, color: str) -> None:
        self.reg_msg.setText(msg)
        self.reg_msg.setStyleSheet(f"color:{color};font-size:12px;font-weight:600;background:transparent;")
        self.reg_msg.setVisible(True)
