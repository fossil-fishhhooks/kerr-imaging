"""Configure TRIG_OUT_2 on the DLP4710 EVM.

Usage:
  python test/dlp_trigger.py [delay_us]

The delay defaults to 0 µs if not specified. Opens the DLP, sets
TRIG_OUT_2, prints the result, then keeps the device open so you
can probe the SMA connector. Press Ctrl+C to exit.
"""

import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from illumination.dlp import (
    DLP_AVAILABLE, dlp_open, dlp_close, dlp_write_trigger_out_config,
)


def main():
    delay = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    if not DLP_AVAILABLE:
        print("DLP not available (wrong platform or missing DLL)")
        sys.exit(1)

    dev = dlp_open()
    if dev is None:
        print("Failed to open DLP device")
        sys.exit(1)

    print(f"Configuring TRIG_OUT_2 with delay={delay} µs ...")
    ret = dlp_write_trigger_out_config(
        dev, select=1, enable=True,
        polarity=False, invert=False, delay=delay,
    )
    if ret == 0:
        print("TRIG_OUT_2 configured successfully (ret=0)")
    else:
        print(f"TRIG_OUT_2 configuration failed (ret={ret})")

    print("\nDLP is open — probe the TRIG_OUT_2 SMA connector now.")
    print("Press Ctrl+C to exit.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    dlp_close(dev)
    print("DLP closed.")


if __name__ == "__main__":
    main()
