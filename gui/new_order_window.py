"""New Order tab — admin/staff order placement.

Customer creation has been moved to the Customer Portal. This tab can only
SEARCH for existing customers, or place an order as Walk-in / No Account.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QRadioButton, QScrollArea, QSpinBox, QTabBar, QTextEdit, QVBoxLayout,
    QWidget
)

from gui.widgets.product_card import ProductCard
from gui.widgets import validators as V
from models.customer import CustomerModel
from models.staff import StaffModel
from services import (
    cart_service, category_service, customer_service, email_service,
    order_service, product_service
)


class OptionsDialog(QDialog):
    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Customize: {product.product_name}")
        self.product = product
        self.selected: list[dict] = []

        layout = QVBoxLayout(self)
        self._group_widgets: list[tuple] = []

        for grp in product.option_groups:
            box = QGroupBox(f"{grp.group_name}{' *' if grp.is_required else ''}")
            v = QVBoxLayout(box)
            ctrls: list = []
            metas: list[dict] = []
            if grp.max_choices == 1:
                bg = QButtonGroup(box)
                for i, item in enumerate(grp.items):
                    rb = QRadioButton(f"{item.option_name}  (+₱{item.additional_price:.2f})")
                    if i == 0 and grp.is_required:
                        rb.setChecked(True)
                    bg.addButton(rb)
                    v.addWidget(rb)
                    ctrls.append(rb)
                    metas.append({"option_name": item.option_name, "additional_price": item.additional_price})
            else:
                for item in grp.items:
                    cb = QCheckBox(f"{item.option_name}  (+₱{item.additional_price:.2f})")
                    v.addWidget(cb)
                    ctrls.append(cb)
                    metas.append({"option_name": item.option_name, "additional_price": item.additional_price})
            layout.addWidget(box)
            self._group_widgets.append((grp, ctrls, metas))

        self.qty = QSpinBox()
        self.qty.setRange(1, max(1, product.quantity_on_hand))
        self.qty.setValue(1)
        qty_row = QHBoxLayout()
        qty_row.addWidget(QLabel("Quantity:"))
        qty_row.addWidget(self.qty)
        qty_row.addStretch(1)
        layout.addLayout(qty_row)

        btns = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Add to Cart")
        ok.setObjectName("primaryBtn")
        ok.clicked.connect(self._confirm)
        btns.addStretch(1)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)

    def _confirm(self) -> None:
        selected: list[dict] = []
        for grp, ctrls, metas in self._group_widgets:
            chosen = [m for c, m in zip(ctrls, metas) if c.isChecked()]
            if grp.is_required and not chosen:
                QMessageBox.warning(self, "Required", f"Please choose an option for {grp.group_name}.")
                return
            if len(chosen) > grp.max_choices:
                QMessageBox.warning(self, "Too many", f"At most {grp.max_choices} for {grp.group_name}.")
                return
            selected.extend(chosen)
        self.selected = selected
        self.accept()


class NewOrderTab(QWidget):
    order_placed = pyqtSignal(int, str)  # (order_id, email_status)

    def __init__(self, current_staff: StaffModel, status_callback=None, parent=None):
        super().__init__(parent)
        self.current_staff = current_staff
        self.status_callback = status_callback or (lambda *_: None)
        self.cart = cart_service.Cart()
        self.selected_customer: CustomerModel | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addWidget(self._build_left_panel(), 2)
        root.addWidget(self._build_center_panel(), 5)
        root.addWidget(self._build_right_panel(), 3)
        V.install_error_qss(self)

    # ---------- LEFT (customer + order info) ----------
    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        layout.addWidget(QLabel("<b>Customer</b>"))

        self.walkin_chk = QCheckBox("Walk-in / No Account")
        self.walkin_chk.toggled.connect(self._toggle_walkin)
        layout.addWidget(self.walkin_chk)

        self.customer_search = QLineEdit()
        self.customer_search.setPlaceholderText("Search customer by name or email…")
        self.customer_search.textChanged.connect(self._refresh_customer_list)
        layout.addWidget(self.customer_search)

        self.customer_combo = QComboBox()
        self.customer_combo.currentIndexChanged.connect(self._on_customer_selected)
        layout.addWidget(self.customer_combo)

        self.cust_info = QLabel("No customer selected")
        self.cust_info.setWordWrap(True)
        self.cust_info.setStyleSheet("color:#6B7280;padding:4px 0;")
        layout.addWidget(self.cust_info)

        self.no_match_lbl = QLabel(
            "<i>Customer not found. They can register via the Customer Portal.</i>"
        )
        self.no_match_lbl.setStyleSheet("color:#9CA3AF;font-size:11px;")
        self.no_match_lbl.setVisible(False)
        layout.addWidget(self.no_match_lbl)

        layout.addSpacing(10)
        layout.addWidget(QLabel("<b>Order Type</b>"))
        type_row = QHBoxLayout()
        self.rb_dine = QRadioButton("Dine-In")
        self.rb_take = QRadioButton("Takeout")
        self.rb_deliv = QRadioButton("Delivery")
        self.rb_dine.setChecked(True)
        for rb in (self.rb_dine, self.rb_take, self.rb_deliv):
            type_row.addWidget(rb)
            rb.toggled.connect(self._update_delivery_visibility)
        layout.addLayout(type_row)

        self.delivery_notes = QTextEdit()
        self.delivery_notes.setPlaceholderText("Delivery address / notes")
        self.delivery_notes.setMaximumHeight(70)
        self.delivery_notes.setVisible(False)
        layout.addWidget(self.delivery_notes)

        layout.addWidget(QLabel("<b>Payment Method</b>"))
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["Cash", "GCash", "Credit Card"])
        layout.addWidget(self.payment_combo)

        layout.addWidget(QLabel("<b>Voucher / Promo Code</b>"))
        promo_row = QHBoxLayout()
        self.voucher_edit = QLineEdit()
        self.voucher_edit.setPlaceholderText("e.g. SAVE10")
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply_voucher)
        promo_row.addWidget(self.voucher_edit)
        promo_row.addWidget(apply_btn)
        layout.addLayout(promo_row)

        self.voucher_status = QLabel("")
        self.voucher_status.setWordWrap(True)
        self.voucher_status.setStyleSheet("font-size:11px;")
        layout.addWidget(self.voucher_status)

        layout.addStretch(1)
        return panel

    # ---------- CENTER (catalog) ----------
    def _build_center_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)

        top = QHBoxLayout()
        top.addWidget(QLabel("<b>Menu</b>"))
        top.addStretch(1)
        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("Search products…")
        self.product_search.setMaximumWidth(280)
        self.product_search.textChanged.connect(self._refresh_product_grid)
        top.addWidget(self.product_search)
        layout.addLayout(top)

        self.cat_tabs = QTabBar()
        self.cat_tabs.setExpanding(False)
        self.cat_tabs.currentChanged.connect(lambda _: self._refresh_product_grid())
        layout.addWidget(self.cat_tabs)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.grid_container)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        layout.addWidget(scroll, 1)
        return panel

    # ---------- RIGHT (cart) ----------
    def _build_right_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel("<b>Cart</b>"))

        self.cart_box = QVBoxLayout()
        cart_inner = QWidget()
        cart_inner.setLayout(self.cart_box)
        cart_scroll = QScrollArea()
        cart_scroll.setWidgetResizable(True)
        cart_scroll.setWidget(cart_inner)
        cart_scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        layout.addWidget(cart_scroll, 1)

        # Sticky totals footer
        footer = QFrame()
        footer.setStyleSheet(
            "QFrame{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;}"
        )
        fl = QVBoxLayout(footer)
        fl.setContentsMargins(12, 10, 12, 10)
        self.subtotal_lbl = QLabel("Subtotal: ₱0.00")
        self.subtotal_lbl.setStyleSheet("color:#374151;")
        self.discount_lbl = QLabel("Discount: -₱0.00")
        self.discount_lbl.setStyleSheet("color:#10B981;")
        self.total_lbl = QLabel("Total: ₱0.00")
        self.total_lbl.setStyleSheet("font-size:20px;font-weight:800;color:#111827;")
        fl.addWidget(self.subtotal_lbl)
        fl.addWidget(self.discount_lbl)
        fl.addWidget(self.total_lbl)
        layout.addWidget(footer)

        place_btn = QPushButton("Place Order")
        place_btn.setObjectName("successBtn")
        place_btn.setMinimumHeight(48)
        place_btn.clicked.connect(self._place_order)
        layout.addWidget(place_btn)
        return panel

    # ---------- Event handlers / refresh ----------
    def refresh(self) -> None:
        self._refresh_customer_list()
        self._refresh_categories()
        self._refresh_product_grid()
        self._refresh_cart()

    def _toggle_walkin(self, on: bool) -> None:
        self.customer_search.setEnabled(not on)
        self.customer_combo.setEnabled(not on)
        if on:
            self.selected_customer = None
            self.cust_info.setText("Walk-in customer (no email confirmation)")
        else:
            self._on_customer_selected(self.customer_combo.currentIndex())

    def _refresh_customer_list(self) -> None:
        prev_id = self.customer_combo.currentData()
        self.customer_combo.blockSignals(True)
        self.customer_combo.clear()
        self.customer_combo.addItem("(no customer selected)", None)
        rows = customer_service.list_customers(self.customer_search.text())
        # only show active accounts
        rows = [c for c in rows if c.is_active]
        for c in rows:
            label = f"{c.full_name} · {c.email}"
            if not c.has_portal_account:
                label += "  (walk-in)"
            self.customer_combo.addItem(label, c.customer_id)
        if prev_id is not None:
            idx = self.customer_combo.findData(prev_id)
            if idx >= 0:
                self.customer_combo.setCurrentIndex(idx)
        self.customer_combo.blockSignals(False)
        # Show no-match hint when search has text but only the placeholder remains
        has_query = bool(self.customer_search.text().strip())
        self.no_match_lbl.setVisible(has_query and self.customer_combo.count() <= 1)

    def _on_customer_selected(self, idx: int) -> None:
        if self.walkin_chk.isChecked():
            return
        cid = self.customer_combo.currentData()
        if not cid:
            self.selected_customer = None
            self.cust_info.setText("No customer selected")
            return
        c = customer_service.get_customer(cid)
        self.selected_customer = c
        if c:
            chip = "<span style='background:#EEF2FF;color:#4338CA;padding:2px 8px;border-radius:8px;font-size:11px;'>Portal Account</span>" if c.has_portal_account else "<span style='background:#F3F4F6;color:#374151;padding:2px 8px;border-radius:8px;font-size:11px;'>Walk-in</span>"
            self.cust_info.setText(
                f"<b>{c.full_name}</b> {chip}<br>{c.email}<br>{c.contact_number or ''}<br>{c.address or ''}"
            )

    def _update_delivery_visibility(self) -> None:
        self.delivery_notes.setVisible(self.rb_deliv.isChecked())

    def _refresh_categories(self) -> None:
        for i in range(self.cat_tabs.count() - 1, -1, -1):
            self.cat_tabs.removeTab(i)
        self.cat_tabs.addTab("All")
        self._cat_ids = [None]
        for c in category_service.list_categories():
            self.cat_tabs.addTab(c["category_name"])
            self._cat_ids.append(c["category_id"])

    def _refresh_product_grid(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        cat_id = None
        idx = self.cat_tabs.currentIndex()
        if 0 <= idx < len(getattr(self, "_cat_ids", [])):
            cat_id = self._cat_ids[idx]

        products = product_service.list_products(
            category_id=cat_id, status="Active",
            search=self.product_search.text(),
        )
        for i, p in enumerate(products):
            card = ProductCard(p)
            card.add_clicked.connect(self._on_add_product)
            self.grid_layout.addWidget(card, i // 4, i % 4)

    def _on_add_product(self, product_id: int) -> None:
        p = product_service.get_product(product_id)
        if not p or p.quantity_on_hand <= 0:
            return
        options: list[dict] = []
        if p.option_groups:
            dlg = OptionsDialog(p, self)
            if not dlg.exec():
                return
            options = dlg.selected
            qty = dlg.qty.value()
        else:
            qty = 1
        existing_qty = sum(
            line["quantity"] for line in self.cart.items.values()
            if line["product_id"] == product_id
        )
        if existing_qty + qty > p.quantity_on_hand:
            QMessageBox.warning(self, "Out of stock",
                                f"Only {p.quantity_on_hand} available, {existing_qty} already in cart.")
            return
        self.cart.add_item(p.product_id, p.product_name, p.product_price,
                           p.quantity_on_hand, qty, options)
        if self.cart.applied_promo:
            self.cart.apply_voucher(self.cart.applied_promo["code"])
        self._refresh_cart()

    def _refresh_cart(self) -> None:
        while self.cart_box.count():
            item = self.cart_box.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        if not self.cart.items:
            empty = QLabel("Your cart is empty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color:#9CA3AF;padding:24px 0;")
            self.cart_box.addWidget(empty)
        else:
            for key, line in list(self.cart.items.items()):
                self.cart_box.addWidget(self._build_cart_row(key, line))

        self.subtotal_lbl.setText(f"Subtotal: ₱{self.cart.subtotal:,.2f}")
        self.discount_lbl.setText(f"Discount: -₱{self.cart.discount_amount:,.2f}")
        self.total_lbl.setText(f"Total: ₱{self.cart.total:,.2f}")

    def _build_cart_row(self, key: str, line: dict) -> QFrame:
        row = QFrame()
        row.setStyleSheet(
            "QFrame{background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px;}"
        )
        rl = QVBoxLayout(row)
        rl.setContentsMargins(10, 8, 10, 8)
        top = QHBoxLayout()
        name = QLabel(f"<b>{line['product_name']}</b>")
        top.addWidget(name, 1)
        rm = QPushButton("✕")
        rm.setMaximumWidth(28)
        rm.clicked.connect(lambda _=False, k=key: self._remove_line(k))
        top.addWidget(rm)
        rl.addLayout(top)
        if line["options"]:
            opt_lbl = QLabel(", ".join(o["option_name"] for o in line["options"]))
            opt_lbl.setStyleSheet("color:#6B7280;font-size:11px;")
            rl.addWidget(opt_lbl)
        bot = QHBoxLayout()
        bot.addWidget(QLabel(f"₱{line['unit_price']:,.2f}"))
        bot.addStretch(1)

        # inline stepper -- 2 +
        minus = QPushButton("−"); minus.setFixedSize(26, 26)
        minus.clicked.connect(lambda _=False, k=key: self._step_qty(k, -1))
        plus = QPushButton("+"); plus.setFixedSize(26, 26)
        plus.clicked.connect(lambda _=False, k=key: self._step_qty(k, +1))
        qty_lbl = QLabel(str(line["quantity"]))
        qty_lbl.setMinimumWidth(24)
        qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qty_lbl.setStyleSheet("font-weight:600;")
        bot.addWidget(minus); bot.addWidget(qty_lbl); bot.addWidget(plus)

        bot.addSpacing(8)
        bot.addWidget(QLabel(f"= <b>₱{line['line_total']:,.2f}</b>"))
        rl.addLayout(bot)
        if line["quantity"] > line["qty_on_hand"]:
            warn = QLabel(f"⚠ Exceeds stock ({line['qty_on_hand']})")
            warn.setStyleSheet("color:#EF4444;font-size:11px;")
            rl.addWidget(warn)
        return row

    def _step_qty(self, key: str, delta: int) -> None:
        if key not in self.cart.items:
            return
        new_q = self.cart.items[key]["quantity"] + delta
        if new_q < 1:
            self._remove_line(key)
            return
        self.cart.update_quantity(key, new_q)
        if self.cart.applied_promo:
            self.cart.apply_voucher(self.cart.applied_promo["code"])
        self._refresh_cart()

    def _remove_line(self, key: str) -> None:
        self.cart.remove_item(key)
        if self.cart.applied_promo:
            self.cart.apply_voucher(self.cart.applied_promo["code"])
        self._refresh_cart()

    def _apply_voucher(self) -> None:
        code = self.voucher_edit.text().strip()
        V.mark_error(self.voucher_edit, False)
        if not code:
            self.cart.remove_voucher()
            self.voucher_status.setText("")
            self._refresh_cart()
            return
        err = V.promo_code(code)
        if err:
            V.mark_error(self.voucher_edit, True)
            self.voucher_status.setStyleSheet("color:#EF4444;font-size:11px;")
            self.voucher_status.setText(err)
            return
        result = self.cart.apply_voucher(code)
        self.voucher_status.setStyleSheet(
            f"color:{'#10B981' if result['is_valid'] else '#EF4444'};font-size:11px;"
        )
        if not result["is_valid"]:
            V.mark_error(self.voucher_edit, True)
        self.voucher_status.setText(result["message"])
        self._refresh_cart()

    def _place_order(self) -> None:
        is_walkin = self.walkin_chk.isChecked()
        if not is_walkin and not self.selected_customer:
            QMessageBox.warning(self, "Customer Required",
                                "Select a customer or check 'Walk-in / No Account'.")
            return
        if not self.cart.items:
            QMessageBox.warning(self, "Empty Cart", "Add at least one item.")
            return
        order_type = "Dine-In" if self.rb_dine.isChecked() else "Takeout" if self.rb_take.isChecked() else "Delivery"
        if order_type == "Delivery":
            notes = self.delivery_notes.toPlainText().strip()
            V.mark_error(self.delivery_notes, False)
            if not notes:
                V.mark_error(self.delivery_notes, True)
                QMessageBox.warning(self, "Delivery Address Required",
                                    "Please enter the delivery address / notes.")
                return
            if len(notes) > 500:
                V.mark_error(self.delivery_notes, True)
                QMessageBox.warning(self, "Too long",
                                    "Delivery notes must be at most 500 characters.")
                return
        # Sanity check stock against cart again
        for line in self.cart.items.values():
            if line["quantity"] > line["qty_on_hand"]:
                QMessageBox.warning(self, "Stock issue",
                                    f"{line['product_name']}: only "
                                    f"{line['qty_on_hand']} in stock.")
                return
        try:
            order_id = order_service.place_order(
                customer_id=None if is_walkin else self.selected_customer.customer_id,
                staff_id=self.current_staff.staff_id,
                cart_items=self.cart.items,
                order_type=order_type,
                payment_method=self.payment_combo.currentText(),
                delivery_notes=self.delivery_notes.toPlainText() if order_type == "Delivery" else "",
                voucher_code=self.cart.applied_promo["code"] if self.cart.applied_promo else None,
                discount_amount=self.cart.discount_amount,
                promotion_id=(self.cart.applied_promo or {}).get("promotion_id"),
                actor_name=self.current_staff.full_name,
            )
        except Exception as e:
            QMessageBox.critical(self, "Order Failed", str(e))
            return

        # Email confirmation only when a real customer with an email is set
        email_status = "Walk-in order — email skipped." if is_walkin else "Email skipped."
        if not is_walkin and self.selected_customer and self.selected_customer.email:
            order = order_service.get_order(order_id)
            if order:
                ok, msg = email_service.send_order_confirmation(order, self.selected_customer, order.items)
                email_status = msg
                if ok:
                    order_service.mark_email_sent(order_id, self.selected_customer.email)

        QMessageBox.information(
            self, "Order Placed",
            f"Order #{order_id} placed successfully.\n\n{email_status}"
        )
        self.cart.clear()
        self.voucher_edit.clear()
        self.voucher_status.setText("")
        self.refresh()
        self.order_placed.emit(order_id, email_status)
