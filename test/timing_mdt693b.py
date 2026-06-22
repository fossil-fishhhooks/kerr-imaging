#!/usr/bin/env python3
"""
Timing benchmark for MDT693B piezo controller serial round-trips.

Measures per-operation breakdown:
  write   – serial write + flush time
  latency – time from write end to first response byte
  read    – time to receive all response bytes (5ms gap detection)
  parse   – time to decode/split/strip response

All measurements use a single connection.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from piezo.NanoMax import NanoMax_MDT693B


def timed(dev, cmd):
    """Send cmd via dev._ser, read with inter-byte gap detection, return
    (lines, write_s, latency_s, read_s, parse_s, total_s)."""
    full = (cmd + "\n").encode()
    ser = dev._ser

    ser.reset_input_buffer()

    t0 = time.perf_counter()
    ser.write(full)
    ser.flush()
    tw = time.perf_counter() - t0

    save_to = ser.timeout
    ser.timeout = None
    tlat_start = time.perf_counter()
    first = ser.read(1)
    tlat = time.perf_counter() - tlat_start
    if not first:
        ser.timeout = save_to
        return (["(timeout)"], tw, tlat, 0, 0, tw + tlat)

    ser.timeout = 0.005
    tread_start = time.perf_counter()
    rest = b""
    while True:
        b = ser.read(1)
        if not b:
            break
        rest += b
    tread = time.perf_counter() - tread_start
    ser.timeout = save_to

    raw = first + rest
    tparse_start = time.perf_counter()
    text = raw.decode("utf-8", errors="replace")
    lines = [l.strip() for l in text.split("\r") if l.strip()]
    lines = [l for l in lines if l != ">"]
    tparse = time.perf_counter() - tparse_start

    total = tw + tlat + tread + tparse
    return lines, tw, tlat, tread, tparse, total


def report_breakdown(label, results, unit="ms"):
    scale = 1000 if unit == "ms" else 1
    print(f"  {label:30s}")
    for name, idx in [("write", 1), ("latency", 2), ("read", 3), ("parse", 4), ("total", 5)]:
        vals = [r[idx] * scale for r in results]
        print(f"    {name:12s}  "
              f"min={min(vals):8.3f}  "
              f"avg={sum(vals)/len(vals):8.3f}  "
              f"max={max(vals):8.3f}  ({unit})  n={len(vals)}")


def report_compact(label, times, unit="ms"):
    scale = 1000 if unit == "ms" else 1
    vals = [t * scale for t in times]
    first = vals[0]
    print(f"  {label:30s}  "
          f"first={first:8.3f}  "
          f"min={min(vals):8.3f}  "
          f"avg={sum(vals)/len(vals):8.3f}  "
          f"max={max(vals):8.3f}  ({unit})  n={len(vals)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MDT693B timing benchmark")
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("-n", type=int, default=10, help="iterations per test")
    args = parser.parse_args()

    N = args.n
    with NanoMax_MDT693B(args.port, baudrate=args.baud) as dev:
        info = dev.id()
        print(f"Connected: MDT693B\n")

        # ── raw serial breakdown ──
        for label, cmd in [
            ("id?  (make/model)",       "id?"),
            ("serial?  (serial#)",      "serial?"),
            ("echo?  (trivial bool)",   "echo?"),
            ("xvoltage?  (query)",      "xvoltage?"),
        ]:
            results = [timed(dev, cmd) for _ in range(N)]
            print(f"  === {label} ===")
            report_breakdown(cmd, results)
            print()

        # set+get
        print(f"  === set X=25 + xvoltage? ===")
        results = []
        for _ in range(N):
            r1 = timed(dev, "xvoltage=25")
            r2 = timed(dev, "xvoltage?")
            combined = (
                r1[0] + r2[0],
                r1[1] + r2[1],
                r1[2] + r2[2],
                r1[3] + r2[3],
                r1[4] + r2[4],
                r1[5] + r2[5],
            )
            results.append(combined)
        report_breakdown("set+get", results)
        print()

        # ── library msg() comparison ──
        print(f"  === Library msg() comparison ===")
        for cmd in ["id?", "serial?", "echo?", "xvoltage?"]:
            times = []
            for _ in range(N):
                t0 = time.perf_counter()
                dev.msg(cmd)
                times.append(time.perf_counter() - t0)
            report_compact(cmd, times)

        dev.allvoltage(0)
        print()
