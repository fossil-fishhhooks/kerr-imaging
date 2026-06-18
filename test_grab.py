"""Test: grab a single frame via snap mode and save to disk.
Run this on the actual camera hardware.
If the saved frame has tearing -> PCIe/DMA issue.
If the saved frame is clean -> issue is in live display code.
"""
import numpy as np
from pylablib.devices import Photometrics

cam = Photometrics.PvcamCamera()
cam.open()

# Snapshot: clean snap mode, single frame, no circular buffer
frame = cam.grab(nframes=1)[0]
height, width = frame.shape

# Save as raw 16-bit
frame.tofile("test_snap.raw")
np.save("test_snap.npy", frame)

# Also grab one frame while in continuous mode (same as live feed)
cam.setup_acquisition(mode="sequence", nframes=100)
cam.start_acquisition()
cam.wait_for_frame()
cont_frame = cam.read_newest_image()
cam.stop_acquisition()

if cont_frame is not None:
    frame.tofile("test_cont.raw")
    np.save("test_cont.npy", cont_frame)

cam.close()

print(f"Snap frame: {width}x{height}")
print(f"Snap frame saved: test_snap.raw, test_snap.npy")
print(f"Continuous frame saved: test_cont.raw, test_cont.npy")
print("Compare both files visually. If snap is clean but cont is torn -> circular buffer issue.")
print("If both are torn -> PCIe posted-write ordering issue (driver-level).")
