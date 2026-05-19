"""Dashboard tab: KPI cards + charts + tables, auto refresh."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget
)

from gui.widgets.data_table import DataTable
from gui.widgets.stat_card import StatCard
from services import report_service

# Charts: gracefully handle missing PyQt6.QtCharts
try:
    from PyQt6.QtCharts import (
        QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView,
        QLineSeries, QPieSeries, QValueAxis,
    )
    HAS_CHARTS = True
except Exception:  # pragma: no cover
    HAS_CHARTS = False


class DashboardTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stats = {}

        # Outer layout holds a single scroll area so the dashboard is usable
        # at any window height.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        outer.addWidget(scroll)

        inner = QWidget()
        scroll.setWidget(inner)
        root = QVBoxLayout(inner)

        # Top: title + period toggle + refresh
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("<h2>Dashboard</h2>"))
        title_row.addStretch(1)
        title_row.addWidget(QLabel("Period:"))
        self.period_combo = QComboBox()
        self.period_combo.addItem("Today", "today")
        self.period_combo.addItem("This Month", "month")
        self.period_combo.addItem("This Year", "year")
        self.period_combo.currentIndexChanged.connect(self.refresh)
        title_row.addWidget(self.period_combo)
        ref = QPushButton("Refresh")
        ref.clicked.connect(self.refresh)
        title_row.addWidget(ref)
        root.addLayout(title_row)

        # KPI cards
        self.cards: dict[str, StatCard] = {}
        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(10)
        kpi_grid.setVerticalSpacing(10)
        for i, (key, label) in enumerate([
            ("period_orders", "Period Orders"),
            ("total_orders", "Total Orders"),
            ("period_revenue", "Period Revenue"),
            ("total_revenue", "Total Revenue"),
            ("total_customers", "Total Customers"),
            ("avg_order_value", "Avg. Order Value"),
        ]):
            card = StatCard(label, "—")
            self.cards[key] = card
            kpi_grid.addWidget(card, i // 3, i % 3)
        root.addLayout(kpi_grid)

        # Charts row
        charts_row = QHBoxLayout()
        if HAS_CHARTS:
            self.bar_view = QChartView()
            self.bar_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.bar_view.setMinimumHeight(220)
            self.bar_view.setMaximumHeight(280)
            self.pie_view = QChartView()
            self.pie_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.pie_view.setMinimumHeight(220)
            self.pie_view.setMaximumHeight(280)
            self.line_view = QChartView()
            self.line_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.line_view.setMinimumHeight(220)
            self.line_view.setMaximumHeight(280)
            charts_row.addWidget(self.bar_view, 1)
            charts_row.addWidget(self.pie_view, 1)
            charts_row.addWidget(self.line_view, 1)
        else:
            charts_row.addWidget(QLabel("Charts disabled (PyQt6.QtCharts not available)."))
        root.addLayout(charts_row)

        # Tables row
        tables_row = QHBoxLayout()
        self.best_table = DataTable(["Product", "Qty Sold", "Revenue"])
        self.recent_table = DataTable(["Order #", "Customer", "Total", "Status", "Date"])
        for t in (self.best_table, self.recent_table):
            t.setMinimumHeight(180)
        tables_row.addWidget(self._wrap("Most Sold Items", self.best_table), 1)
        tables_row.addWidget(self._wrap("Recent Orders", self.recent_table), 1)
        root.addLayout(tables_row, 2)

        # Auto-refresh timer (60 seconds)
        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

        self.refresh()

    def _wrap(self, title: str, w: QWidget) -> QWidget:
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(QLabel(f"<b>{title}</b>"))
        v.addWidget(w)
        return wrap

    def refresh(self) -> None:
        period = self.period_combo.currentData() or "today"
        self._stats = report_service.dashboard_stats(period)
        s = self._stats
        self.cards["period_orders"].set_value(str(s["period_orders"]))
        self.cards["total_orders"].set_value(str(s["total_orders"]))
        self.cards["period_revenue"].set_value(f"₱{s['period_revenue']:,.2f}")
        self.cards["total_revenue"].set_value(f"₱{s['total_revenue']:,.2f}")
        self.cards["total_customers"].set_value(str(s["total_customers"]))
        self.cards["avg_order_value"].set_value(f"₱{s['avg_order_value']:,.2f}")

        # Tables
        self.best_table.set_rows([
            [b["product_name"], str(b["quantity_sold"]), f"₱{b['revenue']:,.2f}"]
            for b in s["best_sellers"]
        ])
        self.recent_table.set_rows([
            [str(r["order_id"]), r["customer_name"], f"₱{r['total']:,.2f}",
             r["status"], r["order_date"]]
            for r in s["recent_orders"]
        ])

        if HAS_CHARTS:
            self._update_charts(s)

    def _update_charts(self, s: dict) -> None:
        from PyQt6.QtGui import QColor
        # Bar: best sellers
        bar_chart = QChart()
        bar_chart.setTitle("Top 5 Best-Selling Products")
        bar_set = QBarSet("Qty Sold")
        bar_set.setColor(QColor("#1E1B4B"))
        cats = []
        for b in s["best_sellers"]:
            bar_set.append(int(b["quantity_sold"]))
            cats.append(b["product_name"][:14])
        if not cats:
            cats = ["—"]
            bar_set.append(0)
        bar_series = QBarSeries()
        bar_series.append(bar_set)
        bar_chart.addSeries(bar_series)
        axis_x = QBarCategoryAxis()
        axis_x.append(cats)
        bar_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        bar_series.attachAxis(axis_x)
        axis_y = QValueAxis()
        bar_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        bar_series.attachAxis(axis_y)
        bar_chart.legend().setVisible(False)
        bar_chart.setBackgroundBrush(QColor("#FFFFFF"))
        self.bar_view.setChart(bar_chart)

        # Pie: order status distribution
        pie_chart = QChart()
        pie_chart.setTitle("Orders by Status")
        pie = QPieSeries()
        palette = ["#1E1B4B", "#10B981", "#F59E0B", "#EF4444", "#6366F1", "#8B5CF6"]
        for i, (status, count) in enumerate((s["status_distribution"] or {"No orders": 1}).items()):
            slice_ = pie.append(f"{status} ({count})", float(count))
            slice_.setColor(QColor(palette[i % len(palette)]))
        pie_chart.addSeries(pie)
        pie_chart.setBackgroundBrush(QColor("#FFFFFF"))
        self.pie_view.setChart(pie_chart)

        # Line: 7-day revenue
        line_chart = QChart()
        line_chart.setTitle("Revenue (last 7 days)")
        line = QLineSeries()
        pen = line.pen()
        pen.setColor(QColor("#1E1B4B"))
        pen.setWidth(2)
        line.setPen(pen)
        for i, t in enumerate(s["trend"]):
            line.append(i, float(t["revenue"]))
        line_chart.addSeries(line)
        ax_x = QBarCategoryAxis()
        ax_x.append([t["date"] for t in s["trend"]])
        line_chart.addAxis(ax_x, Qt.AlignmentFlag.AlignBottom)
        line.attachAxis(ax_x)
        ax_y = QValueAxis()
        line_chart.addAxis(ax_y, Qt.AlignmentFlag.AlignLeft)
        line.attachAxis(ax_y)
        line_chart.legend().setVisible(False)
        line_chart.setBackgroundBrush(QColor("#FFFFFF"))
        self.line_view.setChart(line_chart)
