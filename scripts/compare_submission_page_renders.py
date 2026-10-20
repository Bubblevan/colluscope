"""Compare two Poppler page-render directories pixel by pixel."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--pages", type=int, default=5)
    args = parser.parse_args()

    rows = []
    for page in range(1, args.pages + 1):
        previous = args.previous / f"page-{page}.png"
        current = args.current / f"page-{page}.png"
        if not previous.is_file() or not current.is_file():
            raise SystemExit(f"missing rendered page {page}: {previous} or {current}")
        with Image.open(previous) as left, Image.open(current) as right:
            same_size = left.size == right.size
            same_pixels = same_size and ImageChops.difference(
                left.convert("RGB"), right.convert("RGB")
            ).getbbox() is None
        rows.append({
            "page": page,
            "same_size": same_size,
            "same_pixels": same_pixels,
            "previous_png_sha256": sha256(previous),
            "current_png_sha256": sha256(current),
        })

    result = {"all_pages_pixel_identical": all(row["same_pixels"] for row in rows), "pages": rows}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["all_pages_pixel_identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
