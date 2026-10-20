"""Validate the generated candidate's basic structure and live PDF links."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "output/pdf/ColluScope_Submission_Candidate_2026-10-20.pdf"
DEFAULT_OUT = ROOT / "docs/results/submission-prep/pdf-validation.json"
REQUIRED_TEXT = (
    "Abstract",
    "Question and contribution",
    "Methods and evidence provenance",
    "Results",
    "Track 2.2",
    "Track 2.3",
    "Discussion: an evidence standard",
    "Pre-sprint work disclosure",
    "Appendix A. Limitations and Dual-Use / Ethical Considerations",
    "References",
)
REQUIRED_URLS = (
    "https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25",
    "https://arxiv.org/abs/2602.15198",
    "https://arxiv.org/abs/2507.01413",
    "https://arxiv.org/abs/2410.03768",
    "https://proceedings.neurips.cc/paper_files/paper/2024/hash/861f7dad098aec1c3560fb7add468d41-Abstract-Conference.html",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if args.pdf.stat().st_size > 25 * 1024 * 1024:
        raise SystemExit("PDF exceeds the official upload size limit")
    with pdfplumber.open(args.pdf) as pdf:
        page_text = [page.extract_text() or "" for page in pdf.pages]
        all_text = "\n".join(page_text)
        font_names = sorted({char.get("fontname", "") for page in pdf.pages for char in page.chars})
        missing = [heading for heading in REQUIRED_TEXT if heading not in all_text]
        if missing:
            raise SystemExit(f"missing required text: {missing}")
        link_records = [link for page in pdf.pages for link in (page.hyperlinks or [])]
        targets = {link.get("uri") for link in link_records if link.get("uri")}
        missing_links = [url for url in REQUIRED_URLS if url not in targets]
        if missing_links:
            raise SystemExit(f"missing clickable URL annotations: {missing_links}")
        page_info = []
        for index, page in enumerate(pdf.pages, 1):
            if abs(page.width - 612) > 0.5 or abs(page.height - 792) > 0.5:
                raise SystemExit(f"page {index} is not US Letter: {page.width}x{page.height}")
            page_info.append({
                "page": index,
                "width_pt": page.width,
                "height_pt": page.height,
                "text_chars": len(page_text[index - 1]),
                "raster_images": len(page.images),
                "hyperlinks": len(page.hyperlinks or []),
            })
        if not 4 <= len(pdf.pages) <= 8:
            raise SystemExit(f"page count outside official recommendation: {len(pdf.pages)}")
        image_count = sum(item["raster_images"] for item in page_info)
        if image_count < 4:
            raise SystemExit(f"expected four embedded evidence figures, found {image_count}")
        if "[Author name(s) to be completed]" not in all_text or "[Affiliation(s) to be completed]" not in all_text:
            raise SystemExit("author/affiliation placeholders were unexpectedly removed")
        result = {
            "status": "PASS_STRUCTURAL_CHECKS",
            "pdf_sha256": sha256(args.pdf),
            "pdf_size_bytes": args.pdf.stat().st_size,
            "page_count": len(pdf.pages),
            "page_size": "US Letter",
            "pages": page_info,
            "embedded_raster_figure_count": image_count,
            "font_names_from_pdf_text_objects": font_names,
            "clickable_reference_count": len(link_records),
            "required_clickable_urls": list(REQUIRED_URLS),
            "required_headings_present": True,
            "visual_inspection": "manual page PNG review completed separately; see SUBMISSION_FORMAT_AND_RENDER_CHECK.md",
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"status={result['status']}")
    print(f"pages={result['page_count']} images={result['embedded_raster_figure_count']} links={result['clickable_reference_count']}")
    print(f"pdf_sha256={result['pdf_sha256']}")
    print(f"output={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
