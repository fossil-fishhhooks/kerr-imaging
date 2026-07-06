"""Configure TRIG_OUT_2 on the DLP4710 EVM for oscilloscope sync.

Puts the DLP into External Pattern Streaming mode (1-bit mono) and
sets TRIG_OUT_2 to fire at VSYNC (delay=0) so you can probe the SMA
connector with an oscilloscope and see every pattern frame transition.

TRIG_OUT_1 is also configured for camera sync (delay=171 µs).

Usage:
  python test/dlp_trigger.py [delay_us]

The delay defaults to 0 µs (VSYNC). Press Ctrl+C to exit.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from illumination.dlp import (
    DLP_AVAILABLE, dlp_open, dlp_close,
    dlp_write_input_image_size,
    dlp_write_pattern_config,
    dlp_write_trigger_out_config,
    dlp_set_operate_mode,
    DLP_MODE_EXTERNAL_PATTERN_STREAMING,
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

    print("=== DLP Trigger Out Test ===")
    print()

    # 1. Set input image size (required for pattern mode)
    print("Writing input image size 1920×1080 ...")
    dlp_write_input_image_size(dev, 1920, 1080)

    # 2. Write pattern config: 1-bit mono, 1 pattern, all LEDs
    #    Timing matches TI GUI settings that produce trigger outputs:
    #    exposure=3ms, pre-dark=500µs, post-dark=100µs
    print("Writing pattern config (1-bit mono, 1 pat, all LEDs, 3000µs exp, 500µs pre, 100µs post) ...")
    dlp_write_pattern_config(dev,
        seq_type=0x00, num_patterns=1, illum_sel=0x07,
        exp_time_us=3000, pre_dark_us=500, post_dark_us=100,
    )

    # 3. TRIG_OUT_1 — camera sync at start of illumination (delay = pre-dark)
    print("Configuring TRIG_OUT_1 (camera sync, delay=500 µs) ...")
    dlp_write_trigger_out_config(dev, select=0, enable=True,
                                  polarity=False, invert=False, delay=500)

    # 4. TRIG_OUT_2 — oscilloscope sync at VSYNC (delay=0)
    print(f"Configuring TRIG_OUT_2 (scope sync, delay={delay} µs) ...")
    dlp_write_trigger_out_config(dev, select=1, enable=True,
                                  polarity=False, invert=False, delay=delay)

    # 5. Switch to External Pattern Streaming mode
    print("Switching to External Pattern Streaming mode (0x03) ...")
    dlp_set_operate_mode(dev, DLP_MODE_EXTERNAL_PATTERN_STREAMING)

    print()
    print("DLP is running in External Pattern Streaming mode.")
    print("  TRIG_OUT_1 (SMA J15) — camera sync, delay=500 µs")
    print(f"  TRIG_OUT_2 (SMA J14) — scope sync,  delay={delay} µs")
    print()
    print("Probe both SMA connectors with the oscilloscope.")
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
