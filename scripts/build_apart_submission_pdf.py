from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/submission/colluscope_apart_2026_submission_report.md"
OUTPUT = ROOT / "output/pdf/colluscope_apart_2026_submission_report.pdf"


def inline_markup(text: str) -> str:
    text = escape(text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<link href="\2" color="#155E75">\1</link>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    return text


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def table_rows(lines: list[str]) -> list[list[str]]:
    parsed = [split_table_row(line) for line in lines]
    if len(parsed) > 1 and all(re.fullmatch(r":?-{3,}:?", c.strip()) for c in parsed[1]):
        parsed.pop(1)
    width = max(len(row) for row in parsed)
    return [row + [""] * (width - len(row)) for row in parsed]


def build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PaperTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=21, leading=25, alignment=TA_CENTER, textColor=colors.HexColor("#123047"),
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "PaperSubtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=12, leading=16, alignment=TA_CENTER, textColor=colors.HexColor("#426174"),
            spaceAfter=20,
        ),
        "h1": ParagraphStyle(
            "PaperH1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=15, leading=18, textColor=colors.HexColor("#123047"),
            spaceBefore=13, spaceAfter=7, keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "PaperH2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=11.2, leading=14, textColor=colors.HexColor("#1A526B"),
            spaceBefore=9, spaceAfter=4, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "PaperBody", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9.1, leading=12.4, alignment=TA_LEFT, spaceAfter=6,
            textColor=colors.HexColor("#202B33"),
        ),
        "meta": ParagraphStyle(
            "PaperMeta", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.2, leading=10.2, alignment=TA_CENTER,
            textColor=colors.HexColor("#596B75"), spaceAfter=3,
        ),
        "table": ParagraphStyle(
            "PaperTable", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.1, leading=9.1, textColor=colors.HexColor("#202B33"),
        ),
        "table_header": ParagraphStyle(
            "PaperTableHeader", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.2, leading=9.2, textColor=colors.white,
        ),
        "bullet": ParagraphStyle(
            "PaperBullet", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.9, leading=12.1, leftIndent=10, firstLineIndent=-4, spaceAfter=4,
            textColor=colors.HexColor("#202B33"),
        ),
        "numbered": ParagraphStyle(
            "PaperNumbered", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.9, leading=12.1, leftIndent=15, firstLineIndent=-15, spaceAfter=5,
            textColor=colors.HexColor("#202B33"),
        ),
        "reference": ParagraphStyle(
            "PaperReference", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.7, leading=9.5, leftIndent=14, firstLineIndent=-14, spaceAfter=2,
            textColor=colors.HexColor("#202B33"),
        ),
    }


def page_chrome(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(colors.HexColor("#D7E1E7"))
    canvas.setLineWidth(0.5)
    canvas.line(0.72 * inch, height - 0.46 * inch, width - 0.72 * inch, height - 0.46 * inch)
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(colors.HexColor("#71818A"))
    canvas.drawString(0.72 * inch, height - 0.36 * inch, "COLLUSCOPE | APART AI COLLUSION RESEARCH SPRINT 2026")
    canvas.drawRightString(width - 0.72 * inch, 0.38 * inch, str(doc.page))
    canvas.restoreState()


def parse_markdown(lines: list[str], styles: dict[str, ParagraphStyle]):
    story = []
    i = 0
    first_title = True
    references_mode = False
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("| ") or line.startswith("|"):
            rows = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            data = table_rows(rows)
            formatted = []
            for r_i, row in enumerate(data):
                style = styles["table_header"] if r_i == 0 else styles["table"]
                formatted.append([Paragraph(inline_markup(cell), style) for cell in row])
            available_width = letter[0] - 1.44 * inch
            column_count = max(len(row) for row in data)
            raw_weights = [max(1, max(len(row[c]) for row in data)) ** 0.55 for c in range(column_count)]
            total = sum(raw_weights)
            widths = [available_width * w / total for w in raw_weights]
            table = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#155E75")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F6F8")]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D2DEE4")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.extend([Spacer(1, 3), table, Spacer(1, 7)])
            continue
        if line.startswith("# "):
            text = inline_markup(line[2:])
            if first_title:
                story.append(Paragraph(text, styles["title"]))
                first_title = False
            else:
                story.append(Paragraph(text, styles["h1"]))
            i += 1
            continue
        if line.startswith("## "):
            title = line[3:]
            if title == "References":
                references_mode = True
            if first_title:
                story.append(Paragraph(inline_markup(title), styles["title"]))
                first_title = False
            elif title == "Evidence Boundaries in Multi-Agent Allocation Audits":
                story.append(Paragraph(inline_markup(title), styles["subtitle"]))
            else:
                story.append(Paragraph(inline_markup(title), styles["h1"]))
            i += 1
            continue
        if line.startswith("### "):
            story.append(Paragraph(inline_markup(line[4:]), styles["h2"]))
            i += 1
            continue
        if line.startswith("- "):
            while i < len(lines) and lines[i].strip().startswith("- "):
                item = lines[i].strip()[2:]
                story.append(Paragraph("- " + inline_markup(item), styles["bullet"]))
                i += 1
            story.append(Spacer(1, 3))
            continue
        if re.match(r"^\d+\.\s", line):
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i].strip()):
                style_name = "reference" if references_mode else "numbered"
                story.append(Paragraph(inline_markup(lines[i].strip()), styles[style_name]))
                i += 1
            story.append(Spacer(1, 3))
            continue
        if line == "---":
            story.extend([Spacer(1, 3), HRFlowable(width="100%", color=colors.HexColor("#D7E1E7")), Spacer(1, 6)])
            i += 1
            continue
        if line.startswith("**Authors:**") or line.startswith("**Affiliations:**") or line.startswith("**Team:**") or line.startswith("**Submission track:**") or line.startswith("**Evidence cutoff:**"):
            story.append(Paragraph(inline_markup(line), styles["meta"]))
            i += 1
            continue
        paragraph_lines = [line]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or nxt.startswith(("#", "- ", "|")) or nxt == "---":
                break
            paragraph_lines.append(nxt)
            i += 1
        paragraph = " ".join(paragraph_lines)
        story.append(Paragraph(inline_markup(paragraph), styles["body"]))
    return story


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles()
    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter,
        rightMargin=0.72 * inch, leftMargin=0.72 * inch,
        topMargin=0.68 * inch, bottomMargin=0.64 * inch,
        title="What Agent Traces Can Establish About LLM Collusion",
        author="",
        subject="Evidence boundaries in multi-agent allocation audits",
    )
    document.build(parse_markdown(SOURCE.read_text(encoding="utf-8").splitlines(), styles), onFirstPage=page_chrome, onLaterPages=page_chrome)
    print(OUTPUT)


if __name__ == "__main__":
    main()
