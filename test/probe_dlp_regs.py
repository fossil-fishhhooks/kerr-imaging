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
    print("1) REG[0x0C] bit 0 might control sequential vs simultaneous LED mode.")
    print("   Try: w 0C 01   (enable simultaneous mode)")
    print("   Try: w 0C 00   (back to sequential)")
    print()
    print("2) REG[0x0B] controls LED PWM period. Lower value = higher frequency.")
    print("   Current 0x0B value sets PWM freq. Try halving it:")
    print("     w 0B <current/2>   (e.g., if 0x0B=0xFF, try 0x80)")
    print()
    print("3) REG[0x0D] might enable/disable individual LEDs (bitmask).")
    print("   w 0D 04   (enable green only)")
    print("   w 0D 07   (all LEDs on)")
    print()
    print("4) Try different WriteOperateMode values:")
    print("     mode 00   current mode (normal)")
    print("     mode 01   ? internal pattern?")
    print("     mode 10   ?")
    print()
    print("5) Try different video source formats:")
    print("     format 43   current (24-bit RGB via HDMI)")
    print("     format 00   ? internal test pattern?")
    print("     format 01   ?")
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
