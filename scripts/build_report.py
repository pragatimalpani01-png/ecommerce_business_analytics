"""Build a concise PDF review report from the latest analysis outputs."""
from pathlib import Path
import json
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
    KeepTogether, HRFlowable
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FIG = ROOT / "visualizations"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)
PDF = REPORTS / "marketplace_performance_review.pdf"

NAVY = colors.HexColor("#17324D")
TEAL = colors.HexColor("#168C8C")
ORANGE = colors.HexColor("#E28B43")
MUTED = colors.HexColor("#66788A")
PALE = colors.HexColor("#F2F6F9")
GRID = colors.HexColor("#DCE5EC")


def money(v):
    return "not available" if v is None else f"R$ {v:,.0f}"

def pct(v):
    return "not available" if v is None else f"{100*v:.1f}%"

def footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(GRID)
    canvas.setLineWidth(0.5)
    canvas.line(0.62*inch, 0.48*inch, w-0.62*inch, 0.48*inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    label = "Marketplace performance review | Synthetic demo data" if _DEMO else "Marketplace performance review | Olist public data"
    canvas.drawString(0.62*inch, 0.30*inch, label)
    canvas.drawRightString(w-0.62*inch, 0.30*inch, f"Page {doc.page}")
    canvas.restoreState()

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=26, leading=30, textColor=NAVY, alignment=TA_LEFT, spaceAfter=9))
styles.add(ParagraphStyle(name="SubTitle", parent=styles["Normal"], fontName="Helvetica", fontSize=11, leading=16, textColor=MUTED, spaceAfter=14))
styles.add(ParagraphStyle(name="Section", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=NAVY, spaceBefore=2, spaceAfter=8))
styles.add(ParagraphStyle(name="SubHead", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=TEAL, spaceBefore=6, spaceAfter=4))
styles.add(ParagraphStyle(name="BodyCompact", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.3, leading=13.2, textColor=colors.HexColor("#283B4B"), spaceAfter=6))
styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.1, leading=11, textColor=MUTED, spaceAfter=4))
styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9.5, leading=13.5, textColor=NAVY, spaceAfter=2))
styles.add(ParagraphStyle(name="KPIValue", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=NAVY, alignment=TA_LEFT))
styles.add(ParagraphStyle(name="KPILabel", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.5, leading=9, textColor=MUTED, alignment=TA_LEFT))


def img(name, width=7.05*inch, max_height=4.3*inch):
    p = FIG / name
    if not p.exists(): return Spacer(1, 1)
    im = Image(str(p))
    scale = min(width / im.imageWidth, max_height / im.imageHeight)
    im.drawWidth = im.imageWidth * scale
    im.drawHeight = im.imageHeight * scale
    im.hAlign = "CENTER"
    return im


def section_heading(title, subtitle=None):
    x = [Paragraph(title, styles["Section"])]
    if subtitle: x.append(Paragraph(subtitle, styles["BodyCompact"]))
    x.append(HRFlowable(width="100%", thickness=0.7, color=GRID, spaceBefore=2, spaceAfter=8))
    return x


def main():
    global _DEMO
    metrics_path = OUT / "metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError("Run scripts/analyze.py first.")
    m = json.loads(metrics_path.read_text(encoding="utf-8"))
    _DEMO = m.get("dataset_mode") == "synthetic_demo"
    doc = SimpleDocTemplate(str(PDF), pagesize=A4, rightMargin=0.62*inch, leftMargin=0.62*inch, topMargin=0.58*inch, bottomMargin=0.65*inch, title="Marketplace Performance Review", author="Analytics Project")
    story = []

    # Page 1 - executive cover and scorecard.
    story.append(Paragraph("E-commerce business performance", styles["CoverTitle"]))
    story.append(Paragraph("A review of order value, delivery promises, customer feedback and seller operations", styles["SubTitle"]))
    if _DEMO:
        notice = "DEMO DATA ONLY. The included rows are synthetic and were created to demonstrate the workflow. None of the numbers on this page should be treated as findings about Olist or a real retailer. Run the project against the original public dataset to produce source-data results."
    else:
        notice = "This report uses the historical Olist public dataset. It describes patterns in the available data; it does not establish cause and effect or describe current marketplace performance."
    box = Table([[Paragraph(notice, styles["Callout"])]], colWidths=[7.05*inch])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#FFF5E8" if _DEMO else "#EAF5F4")),
        ("BOX", (0,0), (-1,-1), 0.7, ORANGE if _DEMO else TEAL),
        ("LEFTPADDING", (0,0), (-1,-1), 12), ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 10), ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story.append(box); story.append(Spacer(1, 14))
    story.append(Paragraph("At a glance", styles["Section"]))
    kpis = [
        ("ORDERS", f"{m['order_count']:,}"), ("DELIVERED", f"{m['delivered_orders']:,}"),
        ("DELIVERED ITEM VALUE", money(m["delivered_item_sales_brl"])), ("ON-TIME DELIVERY", pct(m["on_time_delivery_rate"])),
        ("CANCEL RATE", pct(m["cancellation_rate"])), ("AVG. REVIEW", "not available" if m["average_review_score"] is None else f"{m['average_review_score']:.2f} / 5"),
        ("REPEAT-CUSTOMER SHARE", pct(m["repeat_customer_share"])), ("FLAGGED ITEM VALUE", money(m["item_value_in_late_low_review_orders_brl"])),
    ]
    cells = []
    for label, value in kpis:
        cells.append(Paragraph(f"<font color='#66788A' size='7'>{label}</font><br/><font color='#17324D' size='14'><b>{value}</b></font>", styles["BodyCompact"]))
    rows = [cells[:4], cells[4:]]
    scorecard = Table(rows, colWidths=[1.7625*inch]*4, rowHeights=[0.78*inch, 0.78*inch])
    scorecard.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), PALE), ("GRID", (0,0), (-1,-1), 0.6, GRID),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0), (-1,-1), 9),
        ("RIGHTPADDING", (0,0), (-1,-1), 6), ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(scorecard); story.append(Spacer(1, 12))
    story.append(Paragraph("Questions this review is built to answer", styles["SubHead"]))
    for p in [
        "Which months and product categories account for most delivered item value?",
        "How often do orders arrive after the promised date, and how do those experiences line up with reviews?",
        "Which sellers deserve a closer look after allowing for order volume?",
        "What share of customers place another order, and how does that change by first-order month?",
    ]:
        story.append(Paragraph("- " + p, styles["BodyCompact"]))
    story.append(Paragraph("A note on profitability", styles["SubHead"]))
    story.append(Paragraph("The source tables contain item prices and freight values, but not a complete record of cost of goods, refunds, discounts, tax, advertising or operating expenses. This project therefore reports item value and freight burden as business signals. It does not call them profit or margin.", styles["BodyCompact"]))
    story.append(Paragraph(f"Prepared {date.today().strftime('%d %B %Y')}. Currency values are shown in Brazilian reais (BRL).", styles["Small"]))

    # Page 2 - commercial performance.
    story.append(PageBreak())
    story.extend(section_heading("1. Sales and category mix", "Use the monthly trend to see changes in activity; use the category view to decide where to investigate first."))
    story.append(img("monthly_performance.png", width=7.05*inch, max_height=3.5*inch))
    story.append(Spacer(1, 5))
    story.append(Paragraph("The monthly chart separates order count from delivered item value. The value measure excludes freight and is not profit. If a month stands out, check the mix of categories, seller capacity, cancellations and delivery performance before deciding why it changed.", styles["BodyCompact"]))
    story.append(Spacer(1, 3))
    story.append(img("category_opportunity_map.png", width=7.05*inch, max_height=4.15*inch))
    story.append(Paragraph("How to use this view: focus on categories with meaningful item value and a high low-review or late-delivery signal. Review scores belong to orders rather than individual products, so the category-level rating measure is a screening proxy. A dot near the top right is a reason to investigate, not proof of a product-quality problem.", styles["Small"]))

    # Page 3 - delivery and experience.
    story.append(PageBreak())
    story.extend(section_heading("2. Delivery promises and customer feedback", "Actual delivery time and the promised date tell different stories. Keep both measures."))
    story.append(img("promise_gap_distribution.png", width=7.05*inch, max_height=3.55*inch))
    story.append(Paragraph("The promise gap is the actual delivery date minus the estimated delivery date. Positive values indicate late delivery. A median can hide a long tail, so the late share and the range of delays deserve attention as well.", styles["BodyCompact"]))
    story.append(Spacer(1, 5))
    story.append(img("delivery_review_relationship.png", width=7.05*inch, max_height=3.5*inch))
    story.append(Paragraph("Compare review averages across delivery groups, but do not treat this as proof that delay alone caused a review. Price, product mix, customer expectations and other parts of the experience may also matter.", styles["Small"]))

    # Page 4 - sellers and cohort behavior.
    story.append(PageBreak())
    story.extend(section_heading("3. Seller exceptions and repeat-order activity", "These views help narrow a work queue. They are not final judgments about a seller or a customer segment."))
    story.append(img("seller_service_friction.png", width=7.05*inch, max_height=3.8*inch))
    story.append(Paragraph("The service-friction index is a simple screening score: 55% late-delivery share plus 45% low-review share, scaled to 0-100. Sellers only enter the ranking after a minimum order count. Before acting, review sample size, destination mix and product mix.", styles["BodyCompact"]))
    story.append(Spacer(1, 5))
    story.append(img("customer_cohort_activity.png", width=7.05*inch, max_height=3.55*inch))
    story.append(Paragraph("Cohort activity shows which groups of customers placed another order in later months. Newer cohorts have less time to return, so their lower values should not be compared directly with older cohorts.", styles["Small"]))

    # Page 5 - practical next steps and limitations.
    story.append(PageBreak())
    story.extend(section_heading("4. What to do with the findings", "A short list of sensible next steps once the workflow is running against the original dataset."))
    action_rows = [
        [Paragraph("1. Investigate the promise gap", styles["SubHead"]), Paragraph("Start with the destinations, sellers and categories where late delivery is common. Check stock location, carrier hand-offs and whether estimated dates are realistic before changing commercial terms.", styles["BodyCompact"])],
        [Paragraph("2. Give operations a focused queue", styles["SubHead"]), Paragraph("Use the seller scorecard to select exceptions for review. Suppress small samples and ask for a cause before making a seller-level decision.", styles["BodyCompact"])],
        [Paragraph("3. Test a service-recovery pilot", styles["SubHead"]), Paragraph("Contact a defined group of late, low-rated customers, compare the results with a similar group, and track actual costs, review changes and repeat orders. The included planner estimates contact workload and budget only.", styles["BodyCompact"])],
        [Paragraph("4. Add cost data before claiming profit", styles["SubHead"]), Paragraph("Join cost of goods, refunds, discounts and other expenses before estimating margin. Keep item value and freight separate until those costs are available.", styles["BodyCompact"])],
    ]
    act = Table(action_rows, colWidths=[1.55*inch, 5.5*inch])
    act.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"), ("GRID", (0,0), (-1,-1), 0.5, GRID),
        ("BACKGROUND", (0,0), (0,-1), PALE), ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8), ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(act); story.append(Spacer(1, 12))
    story.append(Paragraph("Limits to keep in mind", styles["SubHead"]))
    for p in [
        "The Olist data describes historical orders from 2016 to 2018, not today's marketplace.",
        "Review data is self-selected and not every buyer leaves a review.",
        "Order-level reviews are attached to item lines for category screening; they are not product-specific ratings.",
        "Seller and category patterns are descriptive. They can be affected by order volume, location, product mix and unobserved factors.",
        "Item value associated with a late, low-rated order is not lost revenue or an estimate of recoverable sales.",
    ]:
        story.append(Paragraph("- " + p, styles["BodyCompact"]))
    story.append(Paragraph("Data and attribution", styles["SubHead"]))
    story.append(Paragraph("Olist and Andre Sionek (2018), Brazilian E-Commerce Public Dataset by Olist, Kaggle: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce. The original data is published under CC BY-NC-SA 4.0. Review the dataset page and license terms before redistribution or commercial use.", styles["Small"]))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"PDF report written to {PDF}")

if __name__ == "__main__": main()
