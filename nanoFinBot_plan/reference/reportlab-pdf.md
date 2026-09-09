# reportlab 4.x — reference (PDF)

Pin major 4. Pure Python; builds a PDF to `bytes` with a table + a bar chart.

```python
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart

buf = BytesIO()
doc = SimpleDocTemplate(buf, pagesize=A4)
styles = getSampleStyleSheet()

# summary table
table = Table([[ "Category", "Total" ], ["Food", "250000"], ...])
table.setStyle(TableStyle([
    ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
]))

# bar chart (category totals)
drawing = Drawing(400, 200)
chart = VerticalBarChart()
chart.x, chart.y = 40, 40
chart.width, chart.height = 300, 120
chart.data = [[100000, 50000, ...]]
chart.categoryAxis.categoryNames = ["Food", "Transport", ...]
drawing.add(chart)

story = [Paragraph("Monthly report", styles["Title"]), Spacer(1, 12), table, drawing]
doc.build(story)
pdf_bytes = buf.getvalue()
```

Notes:
- Reportlab's default fonts are the built-in Helvetica/Times; use them (no font file
  needed on Alpine).
- For currency amounts, format via the `CURRENCIES` map in `architecture.md` (code →
  symbol + minor exponent).
