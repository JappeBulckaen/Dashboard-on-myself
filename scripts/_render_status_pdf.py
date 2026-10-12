from pathlib import Path
import sys

sys.path.insert(0, str(Path.home() / "AppData" / "Local" / "Temp" / "dashboard_pdf_lib"))

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUTPUT = Path(__file__).resolve().parents[1] / "Project-Status.pdf"
INK = colors.HexColor("#172B35")
GREEN = colors.HexColor("#173B43")
MINT = colors.HexColor("#F0F4F2")
ACCENT = colors.HexColor("#E6AD4F")
MUTED = colors.HexColor("#52666B")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleCustom", parent=styles["Title"], fontName="Times-Bold", fontSize=23, leading=25, textColor=colors.white, alignment=TA_LEFT, spaceAfter=2))
styles.add(ParagraphStyle(name="SubtitleCustom", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#E0EAEB")))
styles.add(ParagraphStyle(name="Eyebrow", parent=styles["Normal"], fontSize=7, leading=9, textColor=colors.HexColor("#F1C56D")))
styles.add(ParagraphStyle(name="SectionCustom", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=GREEN, spaceBefore=7, spaceAfter=3))
styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontSize=8, leading=10, textColor=INK, spaceAfter=3))
styles.add(ParagraphStyle(name="SmallCustom", parent=styles["BodyText"], fontSize=7, leading=9, textColor=MUTED))
styles.add(ParagraphStyle(name="CardCustom", parent=styles["BodyText"], fontSize=7.5, leading=9, textColor=INK))
styles.add(ParagraphStyle(name="FlowCustom", parent=styles["BodyText"], fontSize=7, leading=9, textColor=GREEN, alignment=TA_LEFT))

P = lambda text, style="BodyCustom": Paragraph(text, styles[style])

def section(title, body):
    return [P(title, "SectionCustom"), P(body)]

story = []
header = Table([
    [P("PROJECT PROGRESS SNAPSHOT", "Eyebrow"), P("12 October 2026", "SmallCustom")],
    [P("Dashboard on Myself", "TitleCustom"), ""],
    [P("A personal KPI dashboard MVP: define goals, see current values, and build toward connected data sources.", "SubtitleCustom"), ""],
], colWidths=[155 * mm, 30 * mm])
header.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), GREEN),
    ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
    ("SPAN", (0, 1), (1, 1)), ("SPAN", (0, 2), (1, 2)),
    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 11),
    ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
    ("TOPPADDING", (0, 1), (-1, 1), 1), ("BOTTOMPADDING", (0, 1), (-1, 1), 1),
    ("TOPPADDING", (0, 2), (-1, 2), 2), ("BOTTOMPADDING", (0, 2), (-1, 2), 9),
    ("LINEBELOW", (0, -1), (-1, -1), 3, ACCENT),
]))
story.append(header)
story.append(Spacer(1, 7))

summary = Table([[
    P("<b>Working foundation</b><br/>Browser UI + FastAPI + PostgreSQL", "CardCustom"),
    P("<b>Core API</b><br/>Health and KPI create/read/update/delete", "CardCustom"),
    P("<b>Backend tests</b><br/>19 passed in latest run", "CardCustom"),
]], colWidths=[61.5 * mm] * 3)
summary.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), MINT),
    ("LINEBEFORE", (0, 0), (-1, -1), 2, colors.HexColor("#438674")),
    ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#DCE4DF")),
    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story.extend([summary, P("How the app fits together", "SectionCustom")])
flow = Table([[
    P("<b>Dashboard</b><br/>HTML / CSS / JavaScript", "FlowCustom"), P("&gt;", "FlowCustom"),
    P("<b>API client</b><br/>fetch requests", "FlowCustom"), P("&gt;", "FlowCustom"),
    P("<b>FastAPI</b><br/>Python endpoints", "FlowCustom"), P("&gt;", "FlowCustom"),
    P("<b>SQLAlchemy</b><br/>database access", "FlowCustom"), P("&gt;", "FlowCustom"),
    P("<b>PostgreSQL</b><br/>persistent data", "FlowCustom"),
]], colWidths=[32 * mm, 4 * mm, 25 * mm, 4 * mm, 25 * mm, 4 * mm, 29 * mm, 4 * mm, 29 * mm])
flow.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), MINT), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE4DF")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story.extend([flow, Spacer(1, 4), P("The browser sends KPI requests to the local API. The API validates them and reads or writes PostgreSQL. The frontend currently points to <b>http://127.0.0.1:8000</b>; this is local development configuration, not a deployed environment.")])
story.append(P("General data schema", "SectionCustom"))

schema_left = [
    "<b>User</b> - owns dashboard data (currently one shared demo user).",
    "<b>MetricCatalog</b> - defines metric name, category, unit, and aggregation.",
    "<b>Goal</b> - stores a user's target, period, and metric reference.",
    "<b>Fact</b> - stores timestamped observed values and their source.",
]
schema_right = [
    "<b>Connection</b> - designed for external provider connection/token metadata.",
    "<b>SyncRun</b> - designed to record connector sync status and results.",
    "<b>DashboardLayout</b> - modeled for saved widget configuration.",
]
left = "<br/>".join(schema_left)
right = "<br/>".join(schema_right)
schema = Table([[P(left, "CardCustom"), P(right, "CardCustom")]], colWidths=[92.25 * mm, 92.25 * mm])
schema.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), MINT), ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#DCE4DF")),
    ("LINEBEFORE", (0, 0), (-1, -1), 2, colors.HexColor("#438674")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
]))
story.extend([schema, Spacer(1, 3), P("A displayed KPI combines a Goal with its MetricCatalog details and latest Fact. Connection, SyncRun, and DashboardLayout are schema foundations, not finished user-facing features.", "SmallCustom")])

left_content = [
    "<b>Set up and verified</b>",
    "- KPI dashboard and create/edit/delete form.<br/>- FastAPI health and KPI CRUD routes.<br/>- PostgreSQL persistence via SQLAlchemy and psycopg.<br/>- Live browser CRUD validated against the API.<br/>- Tests use a disposable PostgreSQL schema per run; 19 passed.<br/>- Mock API remains available; current API URL is hardcoded locally.",
]
right_content = [
    "<b>Still missing / next</b>",
    "- Authentication and per-user data access.<br/>- Real provider authorization, import, scheduling, retries, and sync UI.<br/>- Production/staging configuration and deployed hosting.<br/>- Environment-based frontend API URL.<br/>- Complete browser verification of loading and API-error states.",
]
closing = Table([[P("<br/>".join(left_content), "CardCustom"), P("<br/>".join(right_content), "CardCustom")]], colWidths=[92.25 * mm, 92.25 * mm])
closing.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7F5")), ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#DCE4DF")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
]))
story.extend([Spacer(1, 7), closing, Spacer(1, 5), P("Current scope: alpha/MVP foundation, not a production service. Manual KPI CRUD works; connector-related tables are groundwork only, and no real connector currently imports user data.", "SmallCustom")])

SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=12 * mm, leftMargin=12 * mm, topMargin=10 * mm, bottomMargin=10 * mm, title="Dashboard on Myself - Project Status", author="Project Status").build(story)
print(f"Created {OUTPUT}")
