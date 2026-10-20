"""Rasterize the audited M3 SVG figure for inclusion in a pdfLaTeX paper.

The renderer accepts the deliberately small SVG subset emitted by the M3 audit
(rect, line, text). It reads the immutable audit figure and does not recompute
or alter any plotted values.
"""

from __future__ import annotations

import argparse
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SOURCE_SHA256 = "87be3b5b265381786b01c89cf21ef9dc07fa1dac80491e0bf6257c1005c7f279"
SOURCE = ROOT / "docs/results/m3-mechanism-audit-final/figures/m3_focal_ballot_match.svg"
DEFAULT_OUT = ROOT / "submission-prep/figures/m3_focal_ballot_match.png"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rasterize(source: Path, output: Path, scale: int = 3) -> None:
    if sha256(source) != EXPECTED_SOURCE_SHA256:
        raise SystemExit("source SVG hash differs from the frozen M3 audit artifact")
    root = ET.parse(source).getroot()
    width, height = (int(float(x)) for x in root.attrib["viewBox"].split()[2:])
    image = Image.new("RGB", (width * scale, height * scale), "white")
    draw = ImageDraw.Draw(image)
    font_path = Path(r"C:\Windows\Fonts\arial.ttf")

    def dimension(value: str, full: int) -> float:
        return float(full) if value.endswith("%") else float(value)

    for node in root:
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "rect":
            x, y = float(node.attrib.get("x", 0)), float(node.attrib.get("y", 0))
            w = dimension(node.attrib["width"], width)
            h = dimension(node.attrib["height"], height)
            draw.rectangle((x * scale, y * scale, (x + w) * scale, (y + h) * scale),
                           fill=node.attrib.get("fill", "black"))
        elif tag == "line":
            coords = [float(node.attrib[k]) * scale for k in ("x1", "y1", "x2", "y2")]
            draw.line(coords, fill=node.attrib.get("stroke", "black"), width=scale)
        elif tag == "text":
            size = float(node.attrib.get("font-size", 12))
            font = (ImageFont.truetype(str(font_path), round(size * scale))
                    if font_path.exists() else ImageFont.truetype("arial.ttf", round(size * scale)))
            anchor = {"middle": "ms", "end": "rs", "start": "ls"}.get(
                node.attrib.get("text-anchor", "start"), "ls")
            draw.text((float(node.attrib["x"]) * scale, float(node.attrib["y"]) * scale),
                      node.text or "", fill=node.attrib.get("fill", "black"),
                      font=font, anchor=anchor)
        else:
            raise SystemExit(f"unsupported SVG element in frozen figure: {tag}")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=False, dpi=(300, 300))
    print(f"source_sha256={sha256(source)}")
    print(f"output={output}")
    print(f"output_sha256={sha256(output)}")
    print(f"dimensions={image.width}x{image.height}; scale={scale}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--scale", type=int, default=3)
    args = parser.parse_args()
    rasterize(args.source, args.out, args.scale)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
