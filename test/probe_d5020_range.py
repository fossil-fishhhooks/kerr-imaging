#!/usr/bin/env python3
"""Probe D5020 retardance range by setting and reading back values."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lcd.d5020 import D5020, D5020Error


def probe(dev, port, label, values):
    print(f"  {label}:")
    for v in values:
        try:
            dev.retardance(port, v)
            time.sleep(0.05)
            actual = dev.retardance(port)
            print(f"    set {v:>6.3f}  →  read {actual:.3f}  {'✓' if abs(actual - v) < 0.01 else '⚠ clamped'}")
        except D5020Error as e:
            print(f"    set {v:>6.3f}  →  ERROR: {e}")


if __name__ == "__main__":
    # try DLL next to script, then example dir
    for p in [
        r"C:\Users\Arin\PycharmProjects\cameratest\usbdrvd",
        os.path.dirname(__file__) + r"\usbdrvd",
    ]:
        if os.path.exists(p + ".dll"):
            dll = p
            break
    else:
        dll = r"C:\Users\Arin\PycharmProjects\cameratest\usbdrvd"

    dev = D5020(dll_path=dll)
    n = dev.device_count()
    print(f"Found {n} device(s).\n")

    if n == 0:
        sys.exit(1)

    dev.open(1)
    print(f"Version: {dev.version()}\n")

    # coarse sweep
    coarse = [0, 0.1, 0.25, 0.5, 1, 1.5, 2, 3, 5, 10, 20]
    for port in (0, 1):
        print(f"--- Port {port} ---")
        probe(dev, port, "Coarse sweep", coarse)
        print()

    # fine probe near clamp
    print("--- Fine probe (near clamp point) ---")
    for port in (0, 1):
        actual = dev.retardance(port)
        print(f"  Port {port}:")
        for v in [actual + 0.1, actual + 0.5, actual + 1]:
            dev.retardance(port, v)
            time.sleep(0.05)
            a = dev.retardance(port)
            print(f"    set {v:.3f}  →  read {a:.3f}")
        # restore
        dev.retardance(port, 0)

    dev.close()
