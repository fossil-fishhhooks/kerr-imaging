"""Driver for Photometrics Iris 15 camera via pylablib."""

from pylablib.devices import Photometrics


class Iris15:
    """Wraps pylablib's PvcamCamera for the Photometrics Iris 15."""

    def __init__(self):
        self._cam = None

    def open(self):
        self._cam = Photometrics.PvcamCamera()
        self._cam.open()
        return self

    def close(self):
        if self._cam is not None:
            try:
                self._cam.stop_acquisition()
            except Exception:
                pass
            self._cam.close()
            self._cam = None

    def configure_defaults(self):
        """Apply 2x2 hardware binning + global shutter mode."""
        w, h = self._cam.get_detector_size()
        self._cam.set_roi(0, w, 0, h, hbin=2, vbin=2)
        try:
            self._cam.set_trigger_mode(mode="timed", out_mode="global_shutter")
        except Exception:
            pass
        return self

    # --- pass-through wrappers ---

    def get_detector_size(self):
        return self._cam.get_detector_size()

    def get_roi(self):
        return self._cam.get_roi()

    def set_roi(self, x0, x1, y0, y1, hbin=1, vbin=1):
        self._cam.set_roi(x0, x1, y0, y1, hbin=hbin, vbin=vbin)

    def get_exposure(self):
        return self._cam.get_exposure()

    def set_exposure(self, seconds):
        self._cam.set_exposure(seconds)

    def get_frame_timings(self):
        return self._cam.get_frame_timings()

    def setup_acquisition(self, mode="sequence"):
        self._cam.setup_acquisition(mode=mode)

    def start_acquisition(self):
        self._cam.start_acquisition()

    def stop_acquisition(self):
        self._cam.stop_acquisition()

    def wait_for_frame(self):
        self._cam.wait_for_frame()

    def read_newest_image(self):
        return self._cam.read_newest_image()

    def grab(self, timeout=5):
        return self._cam.grab(timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


if __name__ == "__main__":
    import sys
    import numpy as np

    cam = Iris15()
    try:
        cam.open()
        print("Camera opened")
    except Exception as e:
        print(f"Failed to open camera: {e}")
        sys.exit(1)

    cam.configure_defaults()
    print(f"Detector size: {cam.get_detector_size()}")
    print(f"ROI: {cam.get_roi()}")
    print(f"Frame timings: {cam.get_frame_timings()}")

    cam.setup_acquisition(mode="sequence")
    cam.start_acquisition()
    frame = cam.grab(timeout=5)
    if frame is not None:
        img = frame if isinstance(frame, np.ndarray) else frame[0]
        print(f"Frame shape: {img.shape}, dtype: {img.dtype}")
    cam.stop_acquisition()
    cam.close()
    print("Done")
