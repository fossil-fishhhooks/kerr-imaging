#!/usr/bin/env python3
"""Convert pixel coords from retarder_data into a (mV, waves) calibration table.

Usage: python convert_calibration.py path/to/retarder_data
"""

import re
import sys

CAL_RE = re.compile(r'\(([\d.]+)(\w+),([\d.]+)\s*waves\)\s*=\s*\((\d+),(\d+)\)\s*px')

def load_retarder_data(path):
    with open(path) as f:
        lines = [line.strip() for line in f]

    cal_x = []
    cal_y = []
    data = []

    for i, line in enumerate(lines):
        m = CAL_RE.match(line)
        if m:
            val = float(m.group(1))
            unit = m.group(2).lower()
            waves = float(m.group(3))
            px_x = int(m.group(4))
            px_y = int(m.group(5))
            if waves == 0.0:
                mv = val * 1000 if unit == 'v' else val
                cal_x.append((px_x, mv))
            if val == 0:
                cal_y.append((px_y, waves))
        elif line.startswith('[DATA]'):
            for line in lines[i+1:]:
                if not line or not line[0].isdigit():
                    continue
                parts = line.split(',')
                if len(parts) == 2:
                    data.append((int(parts[0]), int(parts[1])))
            break

    return cal_x, cal_y, data


def fit_linear(points):
    n = len(points)
    sx = sum(p for p, _ in points)
    sy = sum(r for _, r in points)
    sxx = sum(p * p for p, _ in points)
    sxy = sum(p * r for p, r in points)
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    offset = (sy - slope * sx) / n
    return slope, offset


def compact(table, tol=0.008):
    out = [(0, table[0][1])]
    for mv, w in table:
        if abs(w - out[-1][1]) >= tol:
            out.append((int(round(mv)), round(w, 3)))
    if out[-1][0] < table[-1][0]:
        out.append((int(round(table[-1][0])), 0.0))
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'lcvr/docs/retarder_data'
    cal_x, cal_y, data = load_retarder_data(path)
    if not cal_x or not cal_y:
        print("Could not parse calibration", file=sys.stderr)
        sys.exit(1)

    mx, bx = fit_linear(cal_x)
    my, by = fit_linear(cal_y)

    table = []
    for px, py in data:
        mv = max(0, px * mx + bx)
        waves = max(0, py * my + by)
        table.append((mv, waves))

    c = compact(table)
    for mv, w in c:
        print(f"    ({mv}, {w:.3f}),")


if __name__ == '__main__':
    main()
