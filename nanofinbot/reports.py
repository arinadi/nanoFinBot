"""Report generation: PDF summary and CSV export."""

from __future__ import annotations

import csv
from io import BytesIO, StringIO

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from nanofinbot import db


def summarize(transactions: list[dict]) -> dict:
    """Group transactions into per-category income/expense totals by currency."""
    cats: dict[str, dict[str, dict[str, int]]] = {}
    for t in transactions:
        name = t.get("category_name") or "Uncategorized"
        entry = cats.setdefault(name, {"expense": {}, "income": {}})
        ttype = t["type"] if t["type"] in ("expense", "income") else "expense"
        code = t["currency"]
        entry[ttype][code] = entry[ttype].get(code, 0) + (t["amount_minor"] or 0)
    return cats


def _fmt_multi(totals: dict[str, int]) -> str:
    if not totals:
        return "-"
    return ", ".join(db.format_amount(v, code) for code, v in sorted(totals.items()))


def _major_str(minor: int, code: str) -> str:
    exp = db.get_minor_exponent(code)
    if exp == 0:
        return str(minor)
    return f"{minor / (10 ** exp):.{exp}f}"


def _expense_chart(summary: dict) -> Drawing | None:
    names = []
    values = []
    currencies: set[str] = set()
    for name, entry in summary.items():
        for code, v in entry["expense"].items():
            names.append(name)
            values.append(v)
            currencies.add(code)
    if not values or len(currencies) != 1:
        return None
    drawing = Drawing(400, 200)
    chart = VerticalBarChart()
    chart.x, chart.y = 40, 40
    chart.width, chart.height = 320, 130
    chart.data = [values]
    chart.categoryAxis.categoryNames = names
    chart.bars[0].fillColor = colors.HexColor("#4a90d9")
    drawing.add(chart)
    return drawing


def build_pdf(transactions: list[dict], period: str = "current month") -> bytes:
    summary = summarize(transactions)

    total_income: dict[str, int] = {}
    total_expense: dict[str, int] = {}
    for entry in summary.values():
        for code, v in entry["income"].items():
            total_income[code] = total_income.get(code, 0) + v
        for code, v in entry["expense"].items():
            total_expense[code] = total_expense.get(code, 0) + v

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, pageCompression=0)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"nanoFinBot report — {period}", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Income: {_fmt_multi(total_income)}", styles["Normal"]),
        Paragraph(f"Expense: {_fmt_multi(total_expense)}", styles["Normal"]),
        Spacer(1, 12),
    ]

    data = [["Category", "Income", "Expense"]]
    for name in sorted(summary):
        entry = summary[name]
        data.append([name, _fmt_multi(entry["income"]), _fmt_multi(entry["expense"])])
    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(table)

    chart = _expense_chart(summary)
    if chart is not None:
        story.append(Spacer(1, 12))
        story.append(chart)

    doc.build(story)
    return buf.getvalue()


def build_csv(transactions: list[dict]) -> bytes:
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "type", "amount", "currency", "category", "description"])
    for t in transactions:
        writer.writerow(
            [
                t["created_at"],
                t["type"],
                _major_str(t["amount_minor"] or 0, t["currency"]),
                t["currency"],
                t.get("category_name") or "",
                t.get("description") or "",
            ]
        )
    return ("\ufeff" + buf.getvalue()).encode("utf-8")
