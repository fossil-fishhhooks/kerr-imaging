#!/usr/bin/env python3
"""Extract a red calibration curve from a graph screenshot.

Usage:
    python extract_calibration.py path/to/graph.webp

For each pixel column, finds the median y of red-ish pixels
and outputs (column, y) pairs to stdout as CSV.

Use --show to display the detected points overlaid on the graph.
Use --red-threshold N to tune red detection sensitivity (default 60).
"""

import argparse
import csv
import sys
from PIL import Image


def red_score(r, g, b):
    return r - (g + b) // 2


def extract_red_curve(img_path, red_threshold=60, x_range=None, y_range=None):
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    x0, x1 = x_range or (0, w - 1)
    y0, y1 = y_range or (0, h - 1)
    pixels = img.load()

    out = []
    for x in range(x0, x1 + 1):
        red_rows = []
        for y in range(y0, y1 + 1):
            r, g, b = pixels[x, y]
            if red_score(r, g, b) >= red_threshold:
                red_rows.append(y)
        if red_rows:
            mid = sorted(red_rows)[len(red_rows) // 2]
            out.append((x, mid))
    return out, img


def show_curve(img, points):
    try:
        from PIL import ImageDraw
    except ImportError:
        return
    overlay = img.copy()
    draw = ImageDraw.Draw(overlay)
    for x, y in points:
        draw.rectangle([x - 1, y - 1, x + 1, y + 1], fill=(0, 255, 0))
    overlay.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract red calibration curve from graph")
    parser.add_argument("image", help="Path to the graph screenshot (.webp, .png, etc.)")
    parser.add_argument("--red-threshold", type=int, default=60,
                        help="Minimum red score R-(G+B)/2 (default 60)")
    parser.add_argument("--x-range", type=int, nargs=2, default=None,
                        metavar=("X0", "X1"),
                        help="Pixel column range to search (e.g. 140 530)")
    parser.add_argument("--y-range", type=int, nargs=2, default=None,
                        metavar=("Y0", "Y1"),
                        help="Pixel row range to search (e.g. 30 310)")
    parser.add_argument("--show", action="store_true",
                        help="Display the extracted points overlaid on the graph")
    parser.add_argument("--output", "-o",
                        help="Output CSV file (default: stdout)")
    args = parser.parse_args()

    points, img = extract_red_curve(args.image, red_threshold=args.red_threshold,
                                    x_range=args.x_range, y_range=args.y_range)
    if not points:
        print("No red pixels found at threshold", args.red_threshold, file=sys.stderr)
        sys.exit(1)

    out = open(args.output, "w", newline="") if args.output else sys.stdout
    writer = csv.writer(out)
    writer.writerow(["x_pixel", "y_pixel"])
    writer.writerows(points)
    if args.output:
        out.close()
        print(f"Wrote {len(points)} points to {args.output}", file=sys.stderr)

    if args.show:
        show_curve(img, points)
