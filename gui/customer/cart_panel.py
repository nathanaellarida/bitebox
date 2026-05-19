"""Customer cart panel — FoodMeal-style 'Order Menu' card on the right."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QStackedWidget,
    QTextEdit, QVBoxLayout, QWidget
)

from models.customer import CustomerModel
from gui.widgets import validators as V
from services import cart_service, email_service, order_service


# ---------- Checkout dialog (unchanged from the previous version) ----------

class CheckoutDialog(QDialog):
    def __init__(self, cart: cart_service.Cart, customer: CustomerModel, parent=None):
        super().__init__(parent)
        self.cart = cart
        self.customer = customer
        self.placed_order_id: int | None = None
        self.setWindowTitle("Checkout")
        self.setMinimumSize(560, 640)

        v = QVBoxLayout(self)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_step1())
        self.stack.addWidget(self._build_step2())
        v.addWidget(self.stack)
        V.install_error_qss(self)

    def _build_step1(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        # The form may grow tall (Delivery + Credit Card both expanded);
        # wrap it in a scroll area so it always fits.
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(10)

        v.addWidget(QLabel("<h3 style='margin:0;background:transparent;'>Step 1 of 2 · Order Details</h3>"))
        v.addSpacing(6)

        # ---------- Order type ----------
        v.addWidget(self._h("Order Type"))
        type_row = QHBoxLayout()
        self.bg_type = QButtonGroup(self)
        self.btn_dine = self._toggle_btn("Dine-In", checked=True)
        self.btn_take = self._toggle_btn("Takeout")
        self.btn_deliv = self._toggle_btn("Delivery")
        for b in (self.btn_dine, self.btn_take, self.btn_deliv):
            self.bg_type.addButton(b)
            type_row.addWidget(b)
        self.btn_deliv.toggled.connect(self._toggle_delivery)
        v.addLayout(type_row)

        # ---------- Delivery address (structured) ----------
        self.delivery_box = QFrame()
        self.delivery_box.setStyleSheet(
            "QFrame{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;}"
        )
        dl = QVBoxLayout(self.delivery_box)
        dl.setContentsMargins(14, 12, 14, 12)
        dl.setSpacing(8)
        dl.addWidget(self._h("Delivery Address *"))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)
        self.addr_recipient = self._line(self.customer.full_name, "Full name")
        self.addr_phone = self._line(self.customer.contact_number or "",
                                     "Contact number (e.g. 0917-555-1234)")
        # Pre-fill from saved profile address if it's there
        self.addr_street = self._line(self.customer.street or "",
                                      "Street, building, unit #")
        self.addr_city = self._line(self.customer.city or "", "City")
        self.addr_province = self._line(self.customer.province or "",
                                        "Province / State")
        self.addr_postal = self._line(self.customer.postal_code or "",
                                      "Postal code")
        self.addr_landmark = self._line(self.customer.landmark or "",
                                        "Landmark or notes (optional)")
        form.addRow(self._field_label("Recipient *"), self.addr_recipient)
        form.addRow(self._field_label("Contact *"), self.addr_phone)
        form.addRow(self._field_label("Street *"), self.addr_street)

        cp_row = QHBoxLayout()
        cp_row.addWidget(self.addr_city, 2)
        cp_row.addWidget(self.addr_province, 2)
        cp_row.addWidget(self.addr_postal, 1)
        form.addRow(self._field_label("City / Province / Postal *"), cp_row)
        form.addRow(self._field_label("Landmark"), self.addr_landmark)
        dl.addLayout(form)

        # Optional: also persist these fields to the customer's profile
        from PyQt6.QtWidgets import QCheckBox
        self.save_to_profile = QCheckBox(
            "Save this address to my profile for next time"
        )
        self.save_to_profile.setStyleSheet(
            "QCheckBox{color:#374151;font-size:12px;background:transparent;}"
        )
        # Default ON only if profile has no saved address yet
        self.save_to_profile.setChecked(not self.customer.has_delivery_address)
        dl.addWidget(self.save_to_profile)

        self.delivery_box.setVisible(False)
        v.addWidget(self.delivery_box)

        # ---------- Payment ----------
        v.addWidget(self._h("Payment Method"))
        self.payment = QComboBox()
        self.payment.addItems(["Cash", "GCash", "Credit Card"])
        self.payment.currentTextChanged.connect(self._toggle_payment)
        v.addWidget(self.payment)

        # GCash / Credit Card number field, hidden for Cash
        self.payment_box = QFrame()
        self.payment_box.setStyleSheet(
            "QFrame{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;}"
        )
        pl = QVBoxLayout(self.payment_box)
        pl.setContentsMargins(14, 12, 14, 12)
        pl.setSpacing(8)
        self.payment_label = self._h("GCash mobile number *")
        pl.addWidget(self.payment_label)
        self.payment_number = self._line("", "")

        # Optional second row for Credit Card expiry/CVV
        self.cc_row = QHBoxLayout()
        self.cc_expiry = self._line("", "MM/YY")
        self.cc_cvv = self._line("", "CVV")
        self.cc_cvv.setEchoMode(QLineEdit.EchoMode.Password)
        self.cc_row_widget = QWidget()
        rl = QHBoxLayout(self.cc_row_widget)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)
        rl.addWidget(self.cc_expiry, 1)
        rl.addWidget(self.cc_cvv, 1)
        pl.addWidget(self.payment_number)
        pl.addWidget(self.cc_row_widget)
        self.cc_row_widget.setVisible(False)
        self.payment_box.setVisible(False)
        v.addWidget(self.payment_box)

        # ---------- Order summary (read-only) ----------
        v.addSpacing(6)
        v.addWidget(self._h("Order Summary"))
        summary = QFrame()
        summary.setStyleSheet(
            "QFrame{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;}"
        )
        sl = QVBoxLayout(summary)
        sl.setContentsMargins(12, 10, 12, 10)
        for line in self.cart.items.values():
            row = QLabel(
                f"{line['quantity']} × {line['product_name']}  —  "
                f"₱{line['line_total']:,.2f}"
            )
            row.setStyleSheet("padding:2px 0;background:transparent;")
            sl.addWidget(row)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#E5E7EB;")
        sl.addWidget(sep)
        st = QLabel(f"Subtotal: ₱{self.cart.subtotal:,.2f}")
        st.setStyleSheet("background:transparent;")
        sl.addWidget(st)
        if self.cart.discount_amount:
            d = QLabel(f"Discount: -₱{self.cart.discount_amount:,.2f}")
            d.setStyleSheet("color:#10B981;background:transparent;")
            sl.addWidget(d)
        total = QLabel(f"<b>Total: ₱{self.cart.total:,.2f}</b>")
        total.setStyleSheet("font-size:16px;background:transparent;")
        sl.addWidget(total)
        v.addWidget(summary)

        # Inline error label (shown on validation failure)
        self.step1_err = QLabel("")
        self.step1_err.setStyleSheet(
            "color:#EF4444;font-size:12px;font-weight:600;background:transparent;"
        )
        self.step1_err.setWordWrap(True)
        self.step1_err.setVisible(False)
        v.addWidget(self.step1_err)

        v.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        btns = QHBoxLayout()
        btns.setContentsMargins(20, 0, 20, 16)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        nxt = QPushButton("Continue → Confirm")
        nxt.setObjectName("primaryBtn")
        nxt.clicked.connect(self._validate_and_continue)
        btns.addStretch(1); btns.addWidget(cancel); btns.addWidget(nxt)
        outer.addLayout(btns)
        return page

    # ---- helpers ----
    def _h(self, text: str) -> QLabel:
        lbl = QLabel(f"<b>{text}</b>")
        lbl.setStyleSheet("background:transparent;color:#111827;")
        return lbl

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color:#374151;font-weight:600;font-size:12px;background:transparent;"
        )
        return lbl

    def _line(self, value: str, placeholder: str) -> QLineEdit:
        e = QLineEdit(value)
        e.setPlaceholderText(placeholder)
        e.setMinimumHeight(34)
        return e

    def _toggle_btn(self, label: str, checked: bool = False) -> QPushButton:
        b = QPushButton(label)
        b.setCheckable(True)
        b.setChecked(checked)
        b.setObjectName("pillBtn")
        b.setMinimumHeight(38)
        return b

    def _toggle_delivery(self) -> None:
        self.delivery_box.setVisible(self.btn_deliv.isChecked())

    def _toggle_payment(self, value: str) -> None:
        if value == "Cash":
            self.payment_box.setVisible(False)
            return
        self.payment_box.setVisible(True)
        if value == "GCash":
            self.payment_label.setText("<b>GCash mobile number *</b>")
            self.payment_number.setPlaceholderText("e.g. 0917-555-1234")
            self.payment_number.setMaxLength(20)
            self.cc_row_widget.setVisible(False)
        else:  # Credit Card
            self.payment_label.setText("<b>Credit card number *</b>")
            self.payment_number.setPlaceholderText("16-digit card number")
            self.payment_number.setMaxLength(23)
            self.cc_row_widget.setVisible(True)

    # ---- validation ----

    def _validate_and_continue(self) -> None:
        # Reset previous error highlights
        V.clear_errors([
            self.addr_recipient, self.addr_phone, self.addr_street,
            self.addr_city, self.addr_province, self.addr_postal,
            self.addr_landmark, self.payment_number, self.cc_expiry,
            self.cc_cvv,
        ])

        if self.btn_deliv.isChecked():
            err, widget = self._validate_delivery()
            if err:
                if widget is not None:
                    V.mark_error(widget, True)
                return self._set_err(err)
        err, widget = self._validate_payment()
        if err:
            if widget is not None:
                V.mark_error(widget, True)
            return self._set_err(err)
        self.step1_err.setVisible(False)
        self.stack.setCurrentIndex(1)

    def _validate_delivery(self) -> tuple[str | None, object | None]:
        checks: list[tuple[object, str | None]] = [
            (self.addr_recipient, V.name(self.addr_recipient.text(), "Recipient name")),
            (self.addr_phone, V.phone(self.addr_phone.text(), "Contact number")),
            (self.addr_street, V.required(self.addr_street.text(), "Street address")),
            (self.addr_city, V.required(self.addr_city.text(), "City")),
            (self.addr_province, V.required(self.addr_province.text(), "Province")),
            (self.addr_postal, V.postal_code(self.addr_postal.text())),
        ]
        for widget, err in checks:
            if err:
                return err, widget
        if len(self.addr_landmark.text().strip()) > 120:
            return "Landmark must be at most 120 characters.", self.addr_landmark
        return None, None

    def _validate_payment(self) -> tuple[str | None, object | None]:
        method = self.payment.currentText()
        if method == "Cash":
            return None, None
        num = self.payment_number.text()
        if method == "GCash":
            err = V.gcash_number(num)
            return err, (self.payment_number if err else None)
        # Credit Card
        err = V.credit_card(num)
        if err:
            return err, self.payment_number
        err = V.card_expiry(self.cc_expiry.text())
        if err:
            return err, self.cc_expiry
        err = V.card_cvv(self.cc_cvv.text())
        if err:
            return err, self.cc_cvv
        return None, None

    def _set_err(self, msg: str) -> None:
        self.step1_err.setText(msg)
        self.step1_err.setVisible(True)

    # ---- Build delivery_notes string from the structured fields ----
    def _build_delivery_notes(self) -> str:
        if not self.btn_deliv.isChecked():
            return ""
        parts = [
            f"Recipient: {self.addr_recipient.text().strip()}",
            f"Contact: {self.addr_phone.text().strip()}",
            f"Address: {self.addr_street.text().strip()}, "
            f"{self.addr_city.text().strip()}, "
            f"{self.addr_province.text().strip()} "
            f"{self.addr_postal.text().strip()}",
        ]
        landmark = self.addr_landmark.text().strip()
        if landmark:
            parts.append(f"Landmark: {landmark}")
        method = self.payment.currentText()
        num = self.payment_number.text().strip()
        if method == "GCash" and num:
            parts.append(f"GCash: {num}")
        elif method == "Credit Card" and num:
            masked = "**** **** **** " + num.replace(" ", "").replace("-", "")[-4:]
            parts.append(f"Card: {masked}")
        return "\n".join(parts)

    def _build_step2(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 20, 20, 20)

        v.addWidget(QLabel("<h3 style='margin:0'>Step 2 of 2 · Confirm & Place</h3>"))
        v.addSpacing(10)

        info = QFrame()
        info.setStyleSheet("QFrame{background:#EEF2FF;border:1px solid #C7D2FE;border-radius:10px;}")
        il = QVBoxLayout(info)
        il.setContentsMargins(14, 12, 14, 12)
        il.addWidget(QLabel(f"<b>{self.customer.full_name}</b>"))
        il.addWidget(QLabel(self.customer.email))
        v.addWidget(info)
        v.addSpacing(10)

        self.final_total = QLabel("")
        self.final_total.setStyleSheet("font-size:24px;font-weight:800;color:#111827;")
        self.final_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.final_total)
        v.addStretch(1)

        btns = QHBoxLayout()
        back = QPushButton("← Back")
        back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        place = QPushButton("Place Order")
        place.setObjectName("successBtn")
        place.setMinimumHeight(48)
        place.clicked.connect(self._do_place)
        btns.addWidget(back); btns.addStretch(1); btns.addWidget(place)
        v.addLayout(btns)
        return page

    def showEvent(self, event):  # noqa
        super().showEvent(event)
        self.final_total.setText(f"Total Due  —  ₱{self.cart.total:,.2f}")

    def _do_place(self) -> None:
        order_type = ("Dine-In" if self.btn_dine.isChecked()
                      else "Takeout" if self.btn_take.isChecked() else "Delivery")

        # Persist the address to the profile if requested
        if order_type == "Delivery" and self.save_to_profile.isChecked():
            try:
                from services import customer_service
                customer_service.update_profile(
                    self.customer.customer_id,
                    self.customer.first_name, self.customer.last_name,
                    contact_number=self.addr_phone.text(),
                    address=", ".join(p for p in [
                        self.addr_street.text().strip(),
                        self.addr_city.text().strip(),
                        self.addr_province.text().strip(),
                        self.addr_postal.text().strip(),
                    ] if p),
                    street=self.addr_street.text(),
                    city=self.addr_city.text(),
                    province=self.addr_province.text(),
                    postal_code=self.addr_postal.text(),
                    landmark=self.addr_landmark.text(),
                )
                # Refresh the local customer object too
                self.customer = customer_service.get_customer(
                    self.customer.customer_id
                ) or self.customer
            except Exception:
                pass  # never block the order on a profile-save error

        try:
            order_id = order_service.place_order(
                customer_id=self.customer.customer_id,
                staff_id=None,
                cart_items=self.cart.items,
                order_type=order_type,
                payment_method=self.payment.currentText(),
                delivery_notes=self._build_delivery_notes(),
                voucher_code=self.cart.applied_promo["code"] if self.cart.applied_promo else None,
                discount_amount=self.cart.discount_amount,
                promotion_id=(self.cart.applied_promo or {}).get("promotion_id"),
                actor_name=self.customer.full_name + " (customer)",
            )
        except Exception as e:
            QMessageBox.critical(self, "Order Failed", str(e))
            return

        email_status = ""
        order = order_service.get_order(order_id)
        if order and self.customer.email:
            ok, msg = email_service.send_order_confirmation(order, self.customer, order.items)
            email_status = msg
            if ok:
                order_service.mark_email_sent(order_id, self.customer.email)
        self.placed_order_id = order_id

        success = QWidget()
        sv = QVBoxLayout(success)
        sv.setContentsMargins(30, 30, 30, 30)
        sv.addStretch(1)
        check = QLabel("✓"); check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        check.setStyleSheet("font-size:64px;color:#10B981;font-weight:700;")
        sv.addWidget(check)
        h = QLabel(f"Order #{order_id} placed!"); h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.setStyleSheet("font-size:22px;font-weight:800;")
        sv.addWidget(h)
        sub = QLabel(email_status or "Thanks for your order.")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color:#6B7280;")
        sub.setWordWrap(True)
        sv.addWidget(sub)
        sv.addStretch(1)
        close = QPushButton("Done"); close.setObjectName("primaryBtn")
        close.clicked.connect(self.accept)
        sv.addWidget(close)
        self.stack.addWidget(success)
        self.stack.setCurrentWidget(success)


# ---------- Cart panel ----------

class CartPanel(QFrame):
    """Right-column 'Order Menu' card."""
    cart_changed = pyqtSignal()
    order_completed = pyqtSignal(int)

    def __init__(self, customer: CustomerModel, parent=None):
        super().__init__(parent)
        self.setObjectName("customerSideCard")
        self.setMinimumWidth(360)
        self.setMaximumWidth(420)
        self.cart = cart_service.Cart()
        self.customer = customer

        v = QVBoxLayout(self)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(10)
        V.install_error_qss(self)

        head = QHBoxLayout()
        title = QLabel("Order Menu")
        title.setObjectName("sideCardTitle")
        head.addWidget(title)
        head.addStretch(1)
        self.count_lbl = QLabel("0 items")
        self.count_lbl.setObjectName("sideCardSub")
        head.addWidget(self.count_lbl)
        v.addLayout(head)

        # Scrollable list of cart cards
        self.list_box = QVBoxLayout()
        self.list_box.setSpacing(8)
        list_inner = QWidget()
        list_inner.setLayout(self.list_box)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        scroll.setWidget(list_inner)
        v.addWidget(scroll, 1)

        # Totals breakdown
        self.subtotal_lbl = QLabel("Subtotal       ₱0.00")
        self.subtotal_lbl.setStyleSheet("color:#374151;background:transparent;")
        self.discount_lbl = QLabel("Discount       -₱0.00")
        self.discount_lbl.setStyleSheet("color:#10B981;background:transparent;")
        self.discount_lbl.setVisible(False)
        self.total_lbl = QLabel("Total            ₱0.00")
        self.total_lbl.setStyleSheet(
            "font-size:18px;font-weight:800;color:#111827;background:transparent;"
        )
        v.addWidget(self.subtotal_lbl)
        v.addWidget(self.discount_lbl)
        v.addWidget(self.total_lbl)

        # Promo
        promo_card = QFrame()
        promo_card.setObjectName("promoRow")
        promo_card_layout = QHBoxLayout(promo_card)
        promo_card_layout.setContentsMargins(12, 4, 6, 4)
        promo_card_layout.setSpacing(0)
        self.promo_edit = QLineEdit()
        self.promo_edit.setObjectName("promoEdit")
        self.promo_edit.setPlaceholderText("Have a coupon code?")
        promo_card_layout.addWidget(self.promo_edit, 1)
        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("primaryBtn")
        apply_btn.setMaximumWidth(80)
        apply_btn.clicked.connect(self._apply_promo)
        promo_card_layout.addWidget(apply_btn)
        v.addWidget(promo_card)

        self.promo_status = QLabel("")
        self.promo_status.setStyleSheet("font-size:11px;background:transparent;")
        v.addWidget(self.promo_status)

        # Checkout
        self.checkout_btn = QPushButton("Checkout")
        self.checkout_btn.setObjectName("cartCheckoutBtn")
        self.checkout_btn.setMinimumHeight(48)
        self.checkout_btn.clicked.connect(self._checkout)
        self.checkout_btn.setEnabled(False)
        v.addWidget(self.checkout_btn)

        self._refresh()

    # ---------- public ----------
    def add_item(self, product, qty: int, options: list[dict]) -> None:
        existing = sum(line["quantity"] for line in self.cart.items.values()
                       if line["product_id"] == product.product_id)
        if existing + qty > product.quantity_on_hand:
            QMessageBox.warning(self, "Out of stock",
                                f"Only {product.quantity_on_hand} available; "
                                f"{existing} already in cart.")
            return
        self.cart.add_item(product.product_id, product.product_name,
                           product.product_price, product.quantity_on_hand,
                           qty, options)
        if self.cart.applied_promo:
            self.cart.apply_voucher(self.cart.applied_promo["code"])
        self._refresh()

    def item_count(self) -> int:
        return sum(line["quantity"] for line in self.cart.items.values())

    # ---------- internal ----------
    def _refresh(self) -> None:
        while self.list_box.count():
            it = self.list_box.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)

        if not self.cart.items:
            empty = QLabel("Your cart is empty\n\nBrowse the menu to add items.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color:#9CA3AF;padding:40px 0;background:transparent;")
            self.list_box.addWidget(empty)
        else:
            for key, line in list(self.cart.items.items()):
                self.list_box.addWidget(self._build_line(key, line))
            self.list_box.addStretch(1)

        self.subtotal_lbl.setText(f"Subtotal       ₱{self.cart.subtotal:,.2f}")
        self.discount_lbl.setText(f"Discount       -₱{self.cart.discount_amount:,.2f}")
        self.discount_lbl.setVisible(self.cart.discount_amount > 0)
        self.total_lbl.setText(f"Total            ₱{self.cart.total:,.2f}")
        self.checkout_btn.setEnabled(bool(self.cart.items))
        self.count_lbl.setText(f"{self.item_count()} items")
        self.cart_changed.emit()

    def _build_line(self, key: str, line: dict) -> QFrame:
        row = QFrame()
        row.setObjectName("cartLineCard")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(10, 8, 10, 8)
        rl.setSpacing(10)

        # Tiny image / emoji placeholder square
        from gui.customer.assets_loader import product_image, round_pixmap
        thumb = QLabel()
        thumb.setFixedSize(40, 40)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setStyleSheet("background:#FFFFFF;border-radius:10px;font-size:18px;")
        pix = product_image(line["product_name"])
        if pix is not None and not pix.isNull():
            scaled = pix.scaled(
                40, 40,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            thumb.setPixmap(round_pixmap(scaled, 10))
        else:
            thumb.setText("🍽")
        rl.addWidget(thumb)

        center = QVBoxLayout()
        center.setSpacing(2)
        name = QLabel(line["product_name"])
        name.setObjectName("cartLineName")
        name.setWordWrap(True)
        center.addWidget(name)
        if line["options"]:
            ol = QLabel(", ".join(o["option_name"] for o in line["options"]))
            ol.setObjectName("cartLineMeta")
            ol.setWordWrap(True)
            center.addWidget(ol)

        # quantity stepper
        qty_row = QHBoxLayout()
        qty_row.setSpacing(4)
        minus = QPushButton("−"); minus.setObjectName("cartStepBtn")
        minus.clicked.connect(lambda _=False, k=key: self._step(k, -1))
        plus = QPushButton("+"); plus.setObjectName("cartStepBtn")
        plus.clicked.connect(lambda _=False, k=key: self._step(k, +1))
        qty_lbl = QLabel(str(line["quantity"]))
        qty_lbl.setMinimumWidth(20)
        qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qty_lbl.setStyleSheet("font-weight:700;background:transparent;")
        qty_row.addWidget(minus); qty_row.addWidget(qty_lbl); qty_row.addWidget(plus)
        center.addLayout(qty_row)
        rl.addLayout(center, 1)

        right = QVBoxLayout()
        right.setSpacing(4)
        price = QLabel(f"+₱{line['line_total']:,.2f}")
        price.setObjectName("cartLinePrice")
        right.addWidget(price)
        rm = QPushButton("✕")
        rm.setObjectName("cartStepBtn")
        rm.clicked.connect(lambda _=False, k=key: self._remove(k))
        right.addWidget(rm, alignment=Qt.AlignmentFlag.AlignRight)
        rl.addLayout(right)
        return row

    def _step(self, key: str, delta: int) -> None:
        if key not in self.cart.items:
            return
        new_q = self.cart.items[key]["quantity"] + delta
        if new_q < 1:
            self._remove(key); return
        if new_q > self.cart.items[key]["qty_on_hand"]:
            QMessageBox.warning(self, "Out of stock",
                                f"Only {self.cart.items[key]['qty_on_hand']} available.")
            return
        self.cart.update_quantity(key, new_q)
        if self.cart.applied_promo:
            self.cart.apply_voucher(self.cart.applied_promo["code"])
        self._refresh()

    def _remove(self, key: str) -> None:
        self.cart.remove_item(key)
        if self.cart.applied_promo:
            self.cart.apply_voucher(self.cart.applied_promo["code"])
        self._refresh()

    def _apply_promo(self) -> None:
        code = self.promo_edit.text().strip()
        V.mark_error(self.promo_edit, False)
        if not code:
            self.cart.remove_voucher()
            self.promo_status.setText("")
            self._refresh()
            return
        err = V.promo_code(code)
        if err:
            V.mark_error(self.promo_edit, True)
            self.promo_status.setStyleSheet(
                "color:#EF4444;font-size:11px;background:transparent;"
            )
            self.promo_status.setText(err)
            return
        result = self.cart.apply_voucher(code)
        self.promo_status.setStyleSheet(
            f"color:{'#10B981' if result['is_valid'] else '#EF4444'};font-size:11px;background:transparent;"
        )
        if not result["is_valid"]:
            V.mark_error(self.promo_edit, True)
        self.promo_status.setText(result["message"])
        self._refresh()

    def _checkout(self) -> None:
        dlg = CheckoutDialog(self.cart, self.customer, self)
        if dlg.exec() and dlg.placed_order_id is not None:
            order_id = dlg.placed_order_id
            self.cart.clear()
            self.promo_edit.clear()
            self.promo_status.setText("")
            self._refresh()
            self.order_completed.emit(order_id)
