"""Probe DLPC3479 registers to find the LED sequencer / constant-mode control.

Run this on Windows with the DLP connected. It enumerates the DLP, probes several
suspicious registers, and lets you try writes interactively.

DLPC3479 I2C address = 0x1B (7-bit).  Register read = write reg# then read 1 byte.
"""
import ctypes
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from illumination.dlp import (
    DLP_AVAILABLE, dlp_open, dlp_close, dlp_read_operate_mode,
    dlp_write_command, dlp_read_reg, dlp_write_reg,
    dlp_set_rgb_current_max, dlp_set_rgb_current,
    dlp_write_pattern_config, dlp_write_trigger_out_config,
    dlp_write_input_image_size, dlp_read_pattern_config,
    dlp_read_validate_exposure_time,
    dlp_enable_external_pattern_streaming,
    dlp_disable_external_pattern_streaming,
    DLP_MODE_EXTERNAL_PATTERN_STREAMING,
    COLOR_RGB,
)


def probe(dev):
    print("=== Probing DLPC3479 registers ===")
    print()

    # Read operate mode first
    dlp_read_operate_mode(dev)

    print()
    print("Reading suspicious registers...")
    suspicious_regs = [0x05, 0x06, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x33, 0x34, 0x35]
    for reg in suspicious_regs:
        ret, data = dlp_read_reg(dev, reg)
        if ret == 0 and data:
            val = data[0]
            print(f"  REG[0x{reg:02X}] = 0x{val:02X} ({val})")
        else:
            print(f"  REG[0x{reg:02X}] = read failed (ret={ret})")

    print()
    print()
    print("=== Suggested experiments ===")
    print()
    print("=== EXTERNAL PATTERN STREAMING (fixes DMD color-subframe flicker) ===")
    print()
    print("Mode 0x04 = External Pattern Streaming: bypasses DMD R/G/B subframe")
    print("cycling. Each incoming HDMI frame is treated as a single pattern with")
    print("the LED illumination selected in Pattern Config (96h).")
    print()
    print("  stream_on       - enable External Pattern Streaming (mode 0x04)")
    print("  stream_off      - revert to External Video (mode 0x00)")
    print("  patconfig       - write Pattern Config (96h): 8-bit RGB, 1 pat, all LEDs")
    print("                    exp=15000µs, pre=171µs, post=31µs")
    print("  patconfig <st> <n> <il> [exp pre post] - custom (exp/pre/post in µs)")
    print("  patread         - read back Pattern Config (97h)")
    print("  imgsize [w h]  - write Input Image Size (2Eh). default 1920x1080")
    print("  validate [exp]  - ReadValidateExposureTime (9Dh). default exp=15000µs")
    print()
    print("Illumination select byte: b0=R, b1=G, b2=B")
    print("  0x01 = red only, 0x02 = green only, 0x04 = blue only")
    print("  0x07 = all LEDs")
    print()
    print("=== Interactive register writer ===")
    print("Commands:")
    print("  r <reg_hex>         - read register")
    print("  w <reg_hex> <val>   - write register <val>")
    print("  color <name>         - set LED color via WriteRGBCurrentMax")
    print("  mode <val>           - WriteOperateMode(<val>)")
    print("  format <val>         - WriteExternalVideoSourceFormat(<val>)")
    print("  green / red / blue   - set LED to 100% that color, 0 others")
    print("  all                  - set all LEDs to 100%")
    print("  q                    - quit")
    print()

    # We need to import dll functions for mode/format changes
    from illumination.dlp import _dll, DLPDevice
    import illumination.dlp as dlpmod

    while True:
        try:
            line = input("> ").strip()
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()

            if cmd == 'q':
                break

            elif cmd == 'r':
                reg = int(parts[1], 16)
                ret, data = dlp_read_reg(dev, reg)
                if ret == 0 and data:
                    print(f"  REG[0x{reg:02X}] = 0x{data[0]:02X}")
                else:
                    print(f"  read failed ({ret})")

            elif cmd == 'w':
                reg = int(parts[1], 16)
                val = int(parts[2], 16)
                dlp_write_reg(dev, reg, val)
                # read back
                ret, data = dlp_read_reg(dev, reg)
                if ret == 0 and data:
                    print(f"  REG[0x{reg:02X}] -> 0x{data[0]:02X}")

            elif cmd in ('green', 'red', 'blue'):
                r, g, b = COLOR_RGB[cmd.capitalize()]
                dlp_set_rgb_current_max(dev, r, g, b)

            elif cmd == 'all':
                dlp_set_rgb_current_max(dev, 255, 255, 255)

            elif cmd == 'color':
                name = parts[1].capitalize()
                r, g, b = COLOR_RGB[name]
                dlp_set_rgb_current_max(dev, r, g, b)

            elif cmd == 'mode':
                val = int(parts[1], 16)
                ret = _dll.WriteOperateMode(dev, ctypes.c_uint8(val))
                print(f"  WriteOperateMode(0x{val:02X}) = {ret}")

            elif cmd == 'format':
                val = int(parts[1], 16)
                ret = _dll.WriteExternalVideoSourceFormat(dev, ctypes.c_uint8(val))
                print(f"  WriteExternalVideoSourceFormat(0x{val:02X}) = {ret}")

            elif cmd == 'patconfig':
                st = int(parts[1], 16) if len(parts) >= 2 else 0x03
                n = int(parts[2]) if len(parts) >= 3 else 1
                il = int(parts[3], 16) if len(parts) >= 4 else 0x07
                exp = int(parts[4]) if len(parts) >= 5 else 15000
                pre = int(parts[5]) if len(parts) >= 6 else 171
                post = int(parts[6]) if len(parts) >= 7 else 31
                dlp_write_pattern_config(dev, st, n, il, exp, pre, post)

            elif cmd == 'stream_on':
                dlp_enable_external_pattern_streaming(dev)

            elif cmd == 'stream_off':
                dlp_disable_external_pattern_streaming(dev)

            elif cmd == 'patread':
                ret, data = dlp_read_pattern_config(dev)
                if ret == 0 and data:
                    print(f"  Pattern Config: {data.hex()} ({len(data)} bytes)")
                else:
                    print(f"  read failed ({ret})")

            elif cmd == 'imgsize':
                if len(parts) >= 3:
                    w = int(parts[1])
                    h = int(parts[2])
                else:
                    w, h = 1920, 1080
                dlp_write_input_image_size(dev, w, h)

            elif cmd == 'validate':
                exp = int(parts[1]) if len(parts) >= 2 else 15000
                dlp_read_validate_exposure_time(dev, pattern_mode=0x00,
                    bit_depth=0x03, requested_exp_us=exp)

            else:
                print("  unknown command")

        except Exception as e:
            print(f"  error: {e}")


def main():
    if not DLP_AVAILABLE:
        print("DLP not available (wrong platform or missing DLL)")
        return

    print("Opening DLP...")
    dev = dlp_open()
    if not dev:
        print("Failed to open DLP")
        return

    try:
        probe(dev)
    finally:
        dlp_close(dev)
        print("DLP closed")


if __name__ == "__main__":
    main()
