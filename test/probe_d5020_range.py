#!/usr/bin/env python3
"""Probe D5020 retardance range by setting and reading back values."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lcd.d5020 import D5020, D5020Error


def try_query(dev, port, timeout=2):
    try:
        v = dev.retardance(port, timeout=timeout)
        return v
    except D5020Error:
        return None


def probe(dev, port, label, values, timeout=2):
    print(f"  {label}:")
    for v in values:
        try:
            dev.retardance(port, v, timeout=timeout)
            time.sleep(0.05)
            actual = dev.retardance(port, timeout=timeout)
            ok = abs(actual - v) < 0.01
            print(f"    set {v:>6.3f}  ->  read {actual:.3f}  {'OK' if ok else '! clamped'}")
        except D5020Error as e:
            print(f"    set {v:>6.3f}  ->  {e}")


if __name__ == "__main__":
    dev = D5020()
    n = dev.device_count()
    print(f"Found {n} device(s).\n")
    if n == 0:
        sys.exit(1)

    dev.open(1)
    print(f"Version: {dev.version()}\n")

    for port in (0, 1):
        print(f"--- Port {port} ---")
        q = try_query(dev, port)
        if q is None:
            print(f"  Port {port} does not respond (no retarder attached?)")
            print()
            continue
        print(f"  Current retardance: {q:.3f}")

        coarse = [0, 0.1, 0.25, 0.5, 1, 1.5, 2, 3, 5, 10, 20]
        probe(dev, port, "Coarse sweep", coarse)

        print(f"  Restoring to 0...")
        try:
            dev.retardance(port, 0, timeout=2)
        except D5020Error:
            pass
        print()

    dev.close()
