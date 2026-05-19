"""Reports tab — Products and Orders sub-tabs with CSV/PDF export."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget
)

from config import EXPORTS_DIR
from gui.widgets.data_table import DataTable
from services import category_service, order_service, report_service
from services.exporters import OrdersExporter, ProductsExporter


class _ProductsReport(QWidget):
    HEADERS = [
        "ID", "Name", "Category", "Price", "Qty On Hand",
        "Qty Sold", "Revenue", "Status",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        self.cat = QComboBox()
        self.cat.addItem("All categories", None)
        for c in category_service.list_categories():
            self.cat.addItem(c["category_name"], c["category_id"])

        self.status = QComboBox()
        self.status.addItems(["All", "Active", "Inactive"])

        self.df = QDateEdit()
        self.df.setCalendarPopup(True)
        self.df.setDate(date.today() - timedelta(days=30))
        self.dt = QDateEdit()
        self.dt.setCalendarPopup(True)
        self.dt.setDate(date.today())
        self.use_date = QPushButton("Apply Date")
        self.use_date.setCheckable(True)

        run = QPushButton("Run")
        run.setObjectName("primaryBtn")
        run.clicked.connect(self._refresh)

        export_csv = QPushButton("Export CSV")
        export_csv.clicked.connect(self._export_csv)
        export_pdf = QPushButton("Export PDF")
        export_pdf.clicked.connect(self._export_pdf)

        bar.addWidget(QLabel("Category"))
        bar.addWidget(self.cat)
        bar.addWidget(QLabel("Status"))
        bar.addWidget(self.status)
        bar.addWidget(QLabel("From"))
        bar.addWidget(self.df)
        bar.addWidget(QLabel("To"))
        bar.addWidget(self.dt)
        bar.addWidget(self.use_date)
        bar.addStretch(1)
        bar.addWidget(run)
        bar.addWidget(export_csv)
        bar.addWidget(export_pdf)
        layout.addLayout(bar)

        self.table = DataTable(self.HEADERS)
        layout.addWidget(self.table)

        self.summary_lbl = QLabel("Summary: —")
        self.summary_lbl.setStyleSheet("font-weight:600;padding:6px 0;")
        layout.addWidget(self.summary_lbl)

        self._data: list[dict] = []
        self._refresh()

    def _refresh(self) -> None:
        df = self.df.date().toPyDate() if self.use_date.isChecked() else None
        dt = self.dt.date().toPyDate() if self.use_date.isChecked() else None
        self._data = report_service.products_report(
            category_id=self.cat.currentData(),
            status=self.status.currentText(),
            date_from=df, date_to=dt,
        )
        body, colors = [], []
        total_qty_hand, total_qty_sold, total_rev = 0, 0, 0.0
        for r in self._data:
            body.append([
                str(r["product_id"]), r["product_name"], r["category"],
                f"₱{r['price']:,.2f}", str(r["quantity_on_hand"]),
                str(r["quantity_sold"]), f"₱{r['revenue']:,.2f}", r["status"],
            ])
            colors.append(QColor("#fee2e2") if r["quantity_on_hand"] <= 5 else None)
            total_qty_hand += r["quantity_on_hand"]
            total_qty_sold += r["quantity_sold"]
            total_rev += r["revenue"]
        self.table.set_rows(body, colors)
        self.summary_lbl.setText(
            f"Total Qty On Hand: {total_qty_hand}  |  Total Qty Sold: {total_qty_sold}  "
            f"|  Total Revenue: ₱{total_rev:,.2f}"
        )

    def _export_csv(self) -> None:
        if not self._data:
            QMessageBox.information(self, "Empty", "Run the report first.")
            return
        default = str(EXPORTS_DIR / f"products_report_{date.today().isoformat()}.csv")
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", default, "CSV (*.csv)")
        if not path:
            return
        ProductsExporter(self._data).export_csv(path)
        QMessageBox.information(self, "Saved", f"CSV saved:\n{path}")

    def _export_pdf(self) -> None:
        if not self._data:
            QMessageBox.information(self, "Empty", "Run the report first.")
            return
        default = str(EXPORTS_DIR / f"products_report_{date.today().isoformat()}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", default, "PDF (*.pdf)")
        if not path:
            return
        try:
            ProductsExporter(self._data).export_pdf(path)
            QMessageBox.information(self, "Saved", f"PDF saved:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))


class _OrdersReport(QWidget):
    HEADERS = [
        "ID", "Customer", "Email", "Date", "Items", "Subtotal",
        "Discount", "Total", "Type", "Status", "Payment",
        "Email Sent To", "Email Sent At", "Processed By",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()

        self.status = QComboBox()
        self.status.addItems(["All"] + order_service.ORDER_STATUSES)
        self.order_type = QComboBox()
        self.order_type.addItems(["All", "Dine-In", "Takeout", "Delivery"])

        self.df = QDateEdit()
        self.df.setCalendarPopup(True)
        self.df.setDate(date.today() - timedelta(days=30))
        self.dt = QDateEdit()
        self.dt.setCalendarPopup(True)
        self.dt.setDate(date.today())

        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("Customer search…")

        run = QPushButton("Run")
        run.setObjectName("primaryBtn")
        run.clicked.connect(self._refresh)
        csv_btn = QPushButton("Export CSV")
        csv_btn.clicked.connect(self._export_csv)
        pdf_btn = QPushButton("Export PDF")
        pdf_btn.clicked.connect(self._export_pdf)

        bar.addWidget(QLabel("Status"))
        bar.addWidget(self.status)
        bar.addWidget(QLabel("Type"))
        bar.addWidget(self.order_type)
        bar.addWidget(QLabel("From"))
        bar.addWidget(self.df)
        bar.addWidget(QLabel("To"))
        bar.addWidget(self.dt)
        bar.addWidget(self.cust_search, 1)
        bar.addWidget(run)
        bar.addWidget(csv_btn)
        bar.addWidget(pdf_btn)
        layout.addLayout(bar)

        # 14 columns: stretch makes them unreadable. Size to contents and
        # let the table scroll horizontally instead.
        from PyQt6.QtWidgets import QHeaderView
        self.table = DataTable(
            self.HEADERS,
            resize_mode=QHeaderView.ResizeMode.ResizeToContents,
        )
        # Keep the last column from greedy-eating space.
        self.table.horizontalHeader().setStretchLastSection(False)
        layout.addWidget(self.table)

        self.summary_lbl = QLabel("Summary: —")
        self.summary_lbl.setStyleSheet("font-weight:600;padding:6px 0;")
        layout.addWidget(self.summary_lbl)

        self._data: list[dict] = []
        self._refresh()

    def _refresh(self) -> None:
        self._data = report_service.orders_report(
            status=self.status.currentText(),
            order_type=self.order_type.currentText(),
            customer_search=self.cust_search.text(),
            date_from=self.df.date().toPyDate(),
            date_to=self.dt.date().toPyDate(),
        )
        body = [
            [
                str(r["order_id"]), r["customer_name"], r["customer_email"],
                r["order_date"], r["items"][:80], f"₱{r['subtotal']:,.2f}",
                f"₱{r['discount']:,.2f}", f"₱{r['total']:,.2f}",
                r["order_type"], r["status"], r["payment_method"],
                r["email_sent_to"], r["email_sent_at"], r["processed_by"],
            ]
            for r in self._data
        ]
        self.table.set_rows(body)
        total_orders = len(self._data)
        total_revenue = sum(r["total"] for r in self._data)
        total_discount = sum(r["discount"] for r in self._data)
        self.summary_lbl.setText(
            f"Orders: {total_orders}  |  Revenue: ₱{total_revenue:,.2f}  "
            f"|  Discount Given: ₱{total_discount:,.2f}"
        )

    def _export_csv(self) -> None:
        if not self._data:
            QMessageBox.information(self, "Empty", "Run the report first.")
            return
        default = str(EXPORTS_DIR / f"orders_report_{date.today().isoformat()}.csv")
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", default, "CSV (*.csv)")
        if not path:
            return
        OrdersExporter(self._data).export_csv(path)
        QMessageBox.information(self, "Saved", f"CSV saved:\n{path}")

    def _export_pdf(self) -> None:
        if not self._data:
            QMessageBox.information(self, "Empty", "Run the report first.")
            return
        default = str(EXPORTS_DIR / f"orders_report_{date.today().isoformat()}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", default, "PDF (*.pdf)")
        if not path:
            return
        try:
            OrdersExporter(self._data).export_pdf(path)
            QMessageBox.information(self, "Saved", f"PDF saved:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))


class ReportsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        self.products_report = _ProductsReport()
        self.orders_report = _OrdersReport()
        tabs.addTab(self.products_report, "Products Report")
        tabs.addTab(self.orders_report, "Orders Report")
        layout.addWidget(tabs)

    def refresh(self) -> None:
        self.products_report._refresh()
        self.orders_report._refresh()
