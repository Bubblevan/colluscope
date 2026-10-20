"""Build the submission candidate PDF from the editable Markdown source."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from xml.sax.saxutils import escape

import markdown
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "submission-prep/paper.md"
OUTPUT = ROOT / "output/pdf/ColluScope_Submission_Candidate_2026-10-20.pdf"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def abstract_word_count(source: str) -> int:
    match = re.search(r"^## Abstract\s*$(.*?)(?=^##?\s|\Z)", source, re.M | re.S)
    if not match:
        raise ValueError("Markdown source has no Abstract section")
    plain = re.sub(r"[`*_#]", "", match.group(1))
    return len(re.findall(r"\b[\w+/-]+%?\b", plain, re.UNICODE))


class MarkdownFlowables(HTMLParser):
    def __init__(self, source_path: Path, story: list, styles: dict, max_width: float):
        super().__init__(convert_charrefs=True)
        self.source_path = source_path
        self.story = story
        self.styles = styles
        self.max_width = max_width
        self.inline: list[str] = []
        self.block_kind: str | None = None
        self.in_paragraph = False
        self.in_list_item = False
        self.list_type = "ul"
        self.list_index = 0
        self.cell_text: list[str] | None = None
        self.table_rows: list[list[str]] | None = None
        self.current_row: list[str] | None = None
        self.pending_images: list[Image] = []

    def _flush_images(self) -> None:
        if not self.pending_images:
            return
        if len(self.pending_images) == 1:
            self.story.append(self.pending_images[0])
        else:
            gap = 8
            col_width = (self.max_width - gap) / len(self.pending_images)
            cells = []
            for image in self.pending_images:
                scale = min(col_width / image.imageWidth, 180 / image.imageHeight)
                image.drawWidth = image.imageWidth * scale
                image.drawHeight = image.imageHeight * scale
                cells.append(image)
            table = Table([cells], colWidths=[col_width] * len(cells), hAlign="LEFT")
            table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            self.story.append(table)
        self.story.append(Spacer(1, 5))
        self.pending_images.clear()

    def _flush_block(self) -> None:
        text = "".join(self.inline).strip()
        self.inline.clear()
        if not text:
            self.block_kind = None
            return
        self._flush_images()
        if self.block_kind == "li":
            prefix = f"{self.list_index}. " if self.list_type == "ol" else "- "
            text = escape(prefix) + text
        style_name = {
            "h1": "PaperTitle", "h2": "SectionHeading", "h3": "SubsectionHeading",
            "blockquote": "Quote", "li": "Body", "p": "Body",
        }.get(self.block_kind or "p", "Body")
        self.story.append(Paragraph(text, self.styles[style_name]))
        self.story.append(Spacer(1, 3 if style_name == "Body" else 5))
        self.block_kind = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "table":
            self._flush_images()
            self.table_rows = []
        elif tag == "tr" and self.table_rows is not None:
            self.current_row = []
        elif tag in {"td", "th"} and self.current_row is not None:
            self.cell_text = []
        elif tag == "img":
            src = attr.get("src")
            if not src:
                return
            path = (self.source_path.parent / src).resolve()
            with PILImage.open(path) as image:
                px_width, px_height = image.size
            draw_width = self.max_width * 0.86
            draw_height = draw_width * px_height / px_width
            max_height = 165 if "m3_focal_ballot_match" in path.name else 205
            if draw_height > max_height:
                draw_width *= max_height / draw_height
                draw_height = max_height
            self.pending_images.append(Image(str(path), width=draw_width, height=draw_height))
        elif tag in {"p", "h1", "h2", "h3", "blockquote"}:
            if tag == "p" and self.in_list_item:
                return
            self._flush_block()
            self.block_kind = tag
            self.in_paragraph = True
        elif tag in {"ol", "ul"}:
            self.list_type = tag
            self.list_index = 0
        elif tag == "li":
            self._flush_block()
            self.list_index += 1
            self.block_kind = "li"
            self.in_list_item = True
        elif tag in {"strong", "b"}:
            self.inline.append("<b>")
        elif tag in {"em", "i"}:
            self.inline.append("<i>")
        elif tag == "code":
            self.inline.append('<font name="Courier">')
        elif tag == "a":
            href = escape(attr.get("href") or "", {'"': "&quot;"})
            self.inline.append(f'<a href="{href}" color="#125c9e">')
        elif tag == "br":
            self.inline.append("<br/>")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell_text is not None and self.current_row is not None:
            self.current_row.append("".join(self.cell_text).strip())
            self.cell_text = None
        elif tag == "tr" and self.current_row is not None and self.table_rows is not None:
            self.table_rows.append(self.current_row)
            self.current_row = None
        elif tag == "table" and self.table_rows is not None:
            self._render_table(self.table_rows)
            self.table_rows = None
        elif tag in {"p", "h1", "h2", "h3", "blockquote"}:
            if tag == "p" and self.in_list_item:
                return
            self._flush_block()
            self.in_paragraph = False
        elif tag == "li":
            self._flush_block()
            self.in_list_item = False
        elif tag in {"strong", "b"}:
            self.inline.append("</b>")
        elif tag in {"em", "i"}:
            self.inline.append("</i>")
        elif tag == "code":
            self.inline.append("</font>")
        elif tag == "a":
            self.inline.append("</a>")

    def handle_data(self, data: str) -> None:
        if self.cell_text is not None:
            self.cell_text.append(data)
        elif self.block_kind:
            self.inline.append(escape(data))

    def _render_table(self, rows: list[list[str]]) -> None:
        if not rows:
            return
        self._flush_images()
        count = len(rows[0])
        widths = {2: [self.max_width * 0.54, self.max_width * 0.46],
                  3: [self.max_width * 0.46, self.max_width * 0.27, self.max_width * 0.27]}
        col_widths = widths.get(count, [self.max_width / count] * count)
        data = [[Paragraph(escape(value), self.styles["TableHead" if i == 0 else "TableCell"])
                 for value in row] for i, row in enumerate(rows)]
        table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf3")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#132238")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#aab4c0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        self.story.append(KeepTogether([table, Spacer(1, 5)]))


def build(source: Path, output: Path) -> None:
    # Use a fixed PDF timestamp so identical inputs and package versions reproduce bytes.
    os.environ["SOURCE_DATE_EPOCH"] = "1792454400"  # 2026-10-20T00:00:00Z
    source_text = source.read_text(encoding="utf-8")
    abstract_words = abstract_word_count(source_text)
    if abstract_words > 150:
        raise ValueError(f"abstract exceeds 150 words: {abstract_words}")
    if any(ord(character) > 127 for character in source_text):
        raise ValueError("Markdown contains non-ASCII punctuation; use ASCII hyphens and characters")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("PaperTitle", parent=styles["Title"], fontName="Helvetica-Bold",
                              fontSize=17, leading=20, alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle("SectionHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
                              fontSize=12, leading=14, spaceBefore=8, spaceAfter=3, keepWithNext=True))
    styles.add(ParagraphStyle("SubsectionHeading", parent=styles["Heading3"], fontName="Helvetica-Bold",
                              fontSize=10, leading=12, spaceBefore=5, spaceAfter=2, keepWithNext=True))
    styles.add(ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica",
                              fontSize=8.7, leading=11.1, alignment=TA_LEFT, spaceAfter=3,
                              splitLongWords=1, allowWidows=0, allowOrphans=0))
    styles.add(ParagraphStyle("Quote", parent=styles["Body"], leftIndent=12, rightIndent=8,
                              borderColor=colors.HexColor("#98a9ba"), borderWidth=0.5,
                              borderPadding=5, backColor=colors.HexColor("#f4f7fa")))
    styles.add(ParagraphStyle("TableCell", parent=styles["Body"], fontSize=7.8, leading=9.3, spaceAfter=0))
    styles.add(ParagraphStyle("TableHead", parent=styles["TableCell"], fontName="Helvetica-Bold"))

    output.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = letter
    left = right = 0.68 * inch
    top = 0.72 * inch
    bottom = 0.62 * inch
    doc = BaseDocTemplate(str(output), pagesize=letter, leftMargin=left, rightMargin=right,
                          topMargin=top, bottomMargin=bottom, title="What Agent Traces Can Establish",
                          author="[Author name(s) to be completed]")
    frame = Frame(left, bottom, page_width - left - right, page_height - top - bottom,
                  id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def page_chrome(canvas, document):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#647184"))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(left, page_height - 0.42 * inch, "ColluScope | pre-sprint research candidate")
        canvas.drawRightString(page_width - right, 0.36 * inch, f"{document.page}")
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=page_chrome)])
    story: list = []
    html = markdown.markdown(source_text, extensions=["tables", "sane_lists"])
    parser = MarkdownFlowables(source, story, styles, doc.width)
    parser.feed(html)
    parser.close()
    parser._flush_block()
    parser._flush_images()
    doc.build(story)
    print(f"source={source}")
    print(f"source_sha256={sha256(source)}")
    print(f"abstract_words={abstract_words}")
    print(f"output={output}")
    print(f"output_sha256={sha256(output)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    build(args.source, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
