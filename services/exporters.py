"""Object-oriented report exporters built on an abstract base class.

This module demonstrates classic OOP: an abstract template class
(``BaseExporter``) defines the export workflow, while concrete
subclasses (``ProductsExporter``, ``OrdersExporter``) plug in the
report-specific bits (title, summary, row formatting, column widths,
and page orientation). The two ``export_*`` methods are inherited.

The legacy procedural helpers in ``report_service`` (``export_csv``,
``export_pdf``) still exist for backward compatibility; new callers
should prefer the classes here.
"""
from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseExporter(ABC):
    """Abstract template for tabular report exporters.

    Subclasses implement :meth:`title`, :meth:`headers`,
    :meth:`format_row`, :meth:`summary`, :meth:`col_widths`, and
    :meth:`page_size`. The base class handles CSV and PDF rendering.
    """

    # Brand accent colour used for header rows and the summary block.
    ACCENT = "#1E1B4B"
    ACCENT_LIGHT = "#EEF2FF"
    ROW_ALT = "#F8F9FC"

    def __init__(self, data: list[dict], store_name: str | None = None) -> None:
        self.data = data or []
        # Always read the live config so the store name reflects whatever
        # the admin last saved in Settings, even if the caller passes None.
        if not store_name:
            from config import load_config
            store_name = load_config().get("store", {}).get("name", "Store")
        self.store_name = store_name

    # ----- Abstract hooks --------------------------------------------------

    @abstractmethod
    def title(self) -> str:
        """Human-readable report title."""
        raise NotImplementedError

    @abstractmethod
    def headers(self) -> list[str]:
        """Column header labels (display order)."""
        raise NotImplementedError

    @abstractmethod
    def format_row(self, row: dict) -> list[Any]:
        """Convert a raw data dict into a list aligned with ``headers``."""
        raise NotImplementedError

    @abstractmethod
    def summary(self) -> dict[str, Any]:
        """Key/value pairs shown in the summary block above the table."""
        raise NotImplementedError

    @abstractmethod
    def col_widths(self, usable_width: float) -> list[float]:
        """Return per-column widths that sum to ``usable_width`` (points)."""
        raise NotImplementedError

    @abstractmethod
    def page_size(self):
        """Return a reportlab page-size tuple, e.g. ``A4`` or ``landscape(A4)``."""
        raise NotImplementedError

    # ----- Shared CSV export -----------------------------------------------

    def export_csv(self, filepath: str | Path) -> None:
        path = Path(filepath)
        if not self.data:
            path.write_text("(no data)\n", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.headers())
            for row in self.data:
                writer.writerow([self._csv_cell(c) for c in self.format_row(row)])

    # ----- Shared PDF export -----------------------------------------------

    def export_pdf(self, filepath: str | Path) -> None:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table,
            TableStyle,
        )

        PAGE = self.page_size()
        MARGIN = 18 * mm
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=PAGE,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN,
        )
        usable_w = PAGE[0] - 2 * MARGIN

        # ---- Styles --------------------------------------------------------
        base = getSampleStyleSheet()
        s_store = ParagraphStyle(
            "store",
            parent=base["Normal"],
            fontSize=18,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor(self.ACCENT),
            alignment=TA_CENTER,
            spaceAfter=2,
        )
        s_title = ParagraphStyle(
            "rptitle",
            parent=base["Normal"],
            fontSize=13,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#111827"),
            alignment=TA_LEFT,
            spaceAfter=2,
        )
        s_meta = ParagraphStyle(
            "meta",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#6B7280"),
            alignment=TA_LEFT,
            spaceAfter=0,
        )
        s_sum_key = ParagraphStyle(
            "sumkey",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica",
            textColor=colors.HexColor("#374151"),
        )
        s_sum_val = ParagraphStyle(
            "sumval",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#111827"),
            alignment=TA_RIGHT,
        )

        # ---- Header block --------------------------------------------------
        story: list[Any] = [
            Paragraph(self.store_name, s_store),
            HRFlowable(
                width="100%", thickness=1.5,
                color=colors.HexColor(self.ACCENT), spaceAfter=6,
            ),
            Paragraph(self.title(), s_title),
            Paragraph(
                f"Generated: {datetime.now().strftime('%B %d, %Y  %H:%M')}",
                s_meta,
            ),
            Spacer(1, 10),
        ]

        # ---- Summary block -------------------------------------------------
        summary = self.summary()
        if summary:
            items = list(summary.items())
            # Lay out summary as a 2-column table: label | value
            sum_col_w = usable_w * 0.35
            sum_data = [
                [Paragraph(k, s_sum_key), Paragraph(str(v), s_sum_val)]
                for k, v in items
            ]
            sum_table = Table(
                sum_data,
                colWidths=[sum_col_w * 0.65, sum_col_w * 0.35],
                hAlign="LEFT",
            )
            sum_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(self.ACCENT_LIGHT)),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1),
                 [colors.HexColor(self.ACCENT_LIGHT), colors.white]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D2FE")),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#C7D2FE")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(sum_table)
            story.append(Spacer(1, 14))

        # ---- Data table ----------------------------------------------------
        if not self.data:
            story.append(Paragraph("No data to display.", base["Normal"]))
        else:
            col_w = self.col_widths(usable_w)
            headers = self.headers()

            # Header row uses Paragraph so text wraps inside narrow columns.
            s_th = ParagraphStyle(
                "th",
                parent=base["Normal"],
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=colors.white,
                alignment=TA_CENTER,
                leading=10,
            )
            s_td = ParagraphStyle(
                "td",
                parent=base["Normal"],
                fontSize=7.5,
                textColor=colors.HexColor("#111827"),
                leading=10,
            )
            s_td_r = ParagraphStyle(
                "tdr",
                parent=s_td,
                alignment=TA_RIGHT,
            )
            s_td_c = ParagraphStyle(
                "tdc",
                parent=s_td,
                alignment=TA_CENTER,
            )

            # Columns that should be right-aligned (numeric) or centered.
            right_cols = self._right_aligned_cols()
            center_cols = self._center_aligned_cols()

            def _cell(text: str, col_idx: int) -> Paragraph:
                if col_idx in right_cols:
                    return Paragraph(text, s_td_r)
                if col_idx in center_cols:
                    return Paragraph(text, s_td_c)
                return Paragraph(text, s_td)

            header_row = [Paragraph(h, s_th) for h in headers]
            body_rows = [
                [_cell(self._pdf_cell(c), i)
                 for i, c in enumerate(self.format_row(row))]
                for row in self.data
            ]

            table_data = [header_row] + body_rows
            tbl = Table(table_data, colWidths=col_w, repeatRows=1,
                        hAlign="LEFT")

            accent = colors.HexColor(self.ACCENT)
            alt = colors.HexColor(self.ROW_ALT)
            tbl.setStyle(TableStyle([
                # Header
                ("BACKGROUND", (0, 0), (-1, 0), accent),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                # Body
                ("FONTSIZE", (0, 1), (-1, -1), 7.5),
                ("VALIGN", (0, 1), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                # Alternating rows
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, alt]),
                # Grid
                ("LINEBELOW", (0, 0), (-1, -1), 0.25,
                 colors.HexColor("#E5E7EB")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ]))
            story.append(tbl)

        doc.build(story)

    # ----- Cell formatters -------------------------------------------------

    @staticmethod
    def _pdf_cell(value: Any) -> str:
        """Format a value for a PDF table cell (no currency symbol)."""
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, (date, datetime)):
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d %H:%M")
            return value.isoformat()
        return str(value)

    @staticmethod
    def _csv_cell(value: Any) -> str:
        """Format a value for a CSV cell."""
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, (date, datetime)):
            return value.isoformat(sep=" ", timespec="minutes")
        return str(value)

    # ----- Column alignment hints (override in subclasses) -----------------

    def _right_aligned_cols(self) -> set[int]:
        """Return 0-based column indices that should be right-aligned."""
        return set()

    def _center_aligned_cols(self) -> set[int]:
        """Return 0-based column indices that should be center-aligned."""
        return set()


# ---------------------------------------------------------------------------
# Concrete exporters
# ---------------------------------------------------------------------------

class ProductsExporter(BaseExporter):
    """Inventory snapshot — Products report (A4 portrait)."""

    def title(self) -> str:
        return "Products Report"

    def page_size(self):
        from reportlab.lib.pagesizes import A4
        return A4  # portrait — 8 columns fit comfortably

    def headers(self) -> list[str]:
        return ["ID", "Name", "Category", "Price", "Qty On Hand",
                "Qty Sold", "Revenue", "Status"]

    def col_widths(self, usable_width: float) -> list[float]:
        # Proportional weights: ID tiny, Name wide, rest medium
        weights = [0.05, 0.22, 0.15, 0.10, 0.12, 0.10, 0.13, 0.13]
        return [usable_width * w for w in weights]

    def _right_aligned_cols(self) -> set[int]:
        return {3, 4, 5, 6}  # Price, Qty On Hand, Qty Sold, Revenue

    def _center_aligned_cols(self) -> set[int]:
        return {0, 7}  # ID, Status

    def format_row(self, row: dict) -> list[Any]:
        return [
            row.get("product_id"),
            row.get("product_name"),
            row.get("category"),
            row.get("price"),
            row.get("quantity_on_hand"),
            row.get("quantity_sold"),
            row.get("revenue"),
            row.get("status"),
        ]

    def summary(self) -> dict[str, Any]:
        total_revenue = sum(r.get("revenue", 0.0) for r in self.data)
        total_qty_sold = sum(r.get("quantity_sold", 0) for r in self.data)
        total_qty_on_hand = sum(r.get("quantity_on_hand", 0) for r in self.data)
        return {
            "Total Products": len(self.data),
            "Total Qty On Hand": total_qty_on_hand,
            "Total Qty Sold": total_qty_sold,
            "Total Revenue": f"PHP {total_revenue:,.2f}",
        }


class OrdersExporter(BaseExporter):
    """Detailed Orders report — landscape A4 (14 columns)."""

    # Drop the two email-audit columns from the PDF to keep it readable;
    # they are still included in the CSV export.
    _PDF_HEADERS = [
        "ID", "Customer", "Date", "Items",
        "Subtotal", "Discount", "Total",
        "Type", "Status", "Payment", "Processed By",
    ]
    _PDF_KEYS = [
        "order_id", "customer_name", "order_date", "items",
        "subtotal", "discount", "total",
        "order_type", "status", "payment_method", "processed_by",
    ]

    def title(self) -> str:
        return "Orders Report"

    def page_size(self):
        from reportlab.lib.pagesizes import A4, landscape
        return landscape(A4)

    def headers(self) -> list[str]:
        # CSV uses all 14 columns; PDF uses the trimmed set.
        return [
            "ID", "Customer", "Email", "Date", "Items", "Subtotal",
            "Discount", "Total", "Type", "Status", "Payment",
            "Email Sent To", "Email Sent At", "Processed By",
        ]

    def col_widths(self, usable_width: float) -> list[float]:
        # 11 PDF columns — proportional weights
        weights = [0.04, 0.11, 0.13, 0.22, 0.07, 0.06, 0.07,
                   0.07, 0.07, 0.08, 0.08]
        return [usable_width * w for w in weights]

    def _right_aligned_cols(self) -> set[int]:
        return {4, 5, 6}  # Subtotal, Discount, Total

    def _center_aligned_cols(self) -> set[int]:
        return {0, 7, 8, 9}  # ID, Type, Status, Payment

    def format_row(self, row: dict) -> list[Any]:
        # Full row for CSV
        return [
            row.get("order_id"),
            row.get("customer_name"),
            row.get("customer_email"),
            row.get("order_date"),
            row.get("items"),
            row.get("subtotal"),
            row.get("discount"),
            row.get("total"),
            row.get("order_type"),
            row.get("status"),
            row.get("payment_method"),
            row.get("email_sent_to"),
            row.get("email_sent_at"),
            row.get("processed_by"),
        ]

    def _pdf_format_row(self, row: dict) -> list[Any]:
        """Trimmed row for PDF (11 columns, no email-audit fields)."""
        return [row.get(k) for k in self._PDF_KEYS]

    def summary(self) -> dict[str, Any]:
        return {
            "Total Orders": len(self.data),
            "Total Revenue": f"PHP {sum(r.get('total', 0.0) for r in self.data):,.2f}",
            "Discount Given": f"PHP {sum(r.get('discount', 0.0) for r in self.data):,.2f}",
        }

    # Override export_pdf to use the trimmed column set for the table.
    def export_pdf(self, filepath: str | Path) -> None:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table,
            TableStyle,
        )

        PAGE = self.page_size()
        MARGIN = 15 * mm
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=PAGE,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN,
        )
        usable_w = PAGE[0] - 2 * MARGIN

        base = getSampleStyleSheet()
        s_store = ParagraphStyle(
            "store", parent=base["Normal"],
            fontSize=18, fontName="Helvetica-Bold",
            textColor=colors.HexColor(self.ACCENT),
            alignment=TA_CENTER, spaceAfter=2,
        )
        s_title = ParagraphStyle(
            "rptitle", parent=base["Normal"],
            fontSize=13, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#111827"),
            alignment=TA_LEFT, spaceAfter=2,
        )
        s_meta = ParagraphStyle(
            "meta", parent=base["Normal"],
            fontSize=8, textColor=colors.HexColor("#6B7280"),
            alignment=TA_LEFT,
        )
        s_sum_key = ParagraphStyle(
            "sumkey", parent=base["Normal"],
            fontSize=9, fontName="Helvetica",
            textColor=colors.HexColor("#374151"),
        )
        s_sum_val = ParagraphStyle(
            "sumval", parent=base["Normal"],
            fontSize=9, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#111827"),
            alignment=TA_RIGHT,
        )

        story: list[Any] = [
            Paragraph(self.store_name, s_store),
            HRFlowable(
                width="100%", thickness=1.5,
                color=colors.HexColor(self.ACCENT), spaceAfter=6,
            ),
            Paragraph(self.title(), s_title),
            Paragraph(
                f"Generated: {datetime.now().strftime('%B %d, %Y  %H:%M')}",
                s_meta,
            ),
            Spacer(1, 10),
        ]

        summary = self.summary()
        if summary:
            sum_col_w = usable_w * 0.30
            sum_data = [
                [Paragraph(k, s_sum_key), Paragraph(str(v), s_sum_val)]
                for k, v in summary.items()
            ]
            sum_table = Table(
                sum_data,
                colWidths=[sum_col_w * 0.65, sum_col_w * 0.35],
                hAlign="LEFT",
            )
            sum_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1),
                 colors.HexColor(self.ACCENT_LIGHT)),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1),
                 [colors.HexColor(self.ACCENT_LIGHT), colors.white]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D2FE")),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25,
                 colors.HexColor("#C7D2FE")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(sum_table)
            story.append(Spacer(1, 14))

        if not self.data:
            story.append(Paragraph("No data to display.", base["Normal"]))
        else:
            col_w = self.col_widths(usable_w)
            s_th = ParagraphStyle(
                "th", parent=base["Normal"],
                fontSize=7.5, fontName="Helvetica-Bold",
                textColor=colors.white,
                alignment=TA_CENTER, leading=9,
            )
            s_td = ParagraphStyle(
                "td", parent=base["Normal"],
                fontSize=7, textColor=colors.HexColor("#111827"), leading=9,
            )
            s_td_r = ParagraphStyle("tdr", parent=s_td, alignment=TA_RIGHT)
            s_td_c = ParagraphStyle("tdc", parent=s_td, alignment=TA_CENTER)

            right_cols = self._right_aligned_cols()
            center_cols = self._center_aligned_cols()

            def _cell(text: str, col_idx: int) -> Paragraph:
                if col_idx in right_cols:
                    return Paragraph(text, s_td_r)
                if col_idx in center_cols:
                    return Paragraph(text, s_td_c)
                return Paragraph(text, s_td)

            header_row = [Paragraph(h, s_th) for h in self._PDF_HEADERS]
            body_rows = [
                [_cell(self._pdf_cell(c), i)
                 for i, c in enumerate(self._pdf_format_row(row))]
                for row in self.data
            ]

            tbl = Table(
                [header_row] + body_rows,
                colWidths=col_w,
                repeatRows=1,
                hAlign="LEFT",
            )
            accent = colors.HexColor(self.ACCENT)
            alt = colors.HexColor(self.ROW_ALT)
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), accent),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, 0), 5),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("VALIGN", (0, 1), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 1), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, alt]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25,
                 colors.HexColor("#E5E7EB")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ]))
            story.append(tbl)

        doc.build(story)
