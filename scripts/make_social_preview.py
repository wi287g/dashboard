"""
make_social_preview.py
======================
Crop and resize any screenshot to a 1200×630 og:image / twitter:image card.

Usage
-----
  python scripts/make_social_preview.py PATH_TO_SCREENSHOT
  python scripts/make_social_preview.py PATH_TO_SCREENSHOT --out docs/img/social-preview.png

Dependencies
------------
  pip install Pillow
"""
import argparse
import sys
from pathlib import Path

TARGET_W, TARGET_H = 1200, 630

def make_preview(src: Path, dst: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        sys.exit("ERROR: Pillow not installed — run: pip install Pillow")

    img = Image.open(src).convert("RGB")
    src_w, src_h = img.size
    print(f"Source: {src_w}×{src_h}")

    # Scale so the image fully covers the target (cover strategy, then center-crop)
    scale = max(TARGET_W / src_w, TARGET_H / src_h)
    new_w, new_h = round(src_w * scale), round(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Center crop to 1200×630
    left = (new_w - TARGET_W) // 2
    top  = (new_h - TARGET_H) // 2
    img  = img.crop((left, top, left + TARGET_W, top + TARGET_H))

    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "PNG", optimize=True)
    print(f"✓ Saved {TARGET_W}×{TARGET_H} social preview → {dst}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Input screenshot path")
    parser.add_argument("--out", default="docs/img/social-preview.png", help="Output path")
    args = parser.parse_args()

    make_preview(Path(args.source), Path(args.out))
