import numpy as np
from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSpinBox, QDoubleSpinBox, QCheckBox, QSlider
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap


class CameraPanel(QGroupBox):
    def __init__(self, cam=None, log_callback=None, parent=None):
        super().__init__("Camera", parent)
        self._log = log_callback or (lambda msg: None)
        self._cam = cam
        self._capturing = False
        self._frame_count = 0
        self._framebuffer = None
        self._snapshot = None
        self._build_ui()

        if cam is not None:
            self._init_from_cam()

    def _log_msg(self, msg):
        self._log(f"\n[CAM] {msg}")

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- Connect / status row ---
        top = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._toggle_connect)
        self._status = QLabel("Disconnected")
        self._status.setStyleSheet("color: gray")
        top.addWidget(self._connect_btn)
        top.addWidget(self._status)
        top.addStretch()
        layout.addLayout(top)

        # --- Live feed label ---
        self._live_label = QLabel("No camera")
        self._live_label.setAlignment(Qt.AlignCenter)
        self._live_label.setMinimumHeight(160)
        self._live_label.setStyleSheet("border: 1px solid #555")
        layout.addWidget(self._live_label)

        # --- Capture toggle ---
        cap_row = QHBoxLayout()
        self._capture_btn = QPushButton("Start Capture")
        self._capture_btn.setEnabled(False)
        self._capture_btn.clicked.connect(self._toggle_capture)
        self._fps_label = QLabel("FPS: --")
        self._cam_status = QLabel("")
        cap_row.addWidget(self._capture_btn)
        cap_row.addWidget(self._fps_label)
        cap_row.addWidget(self._cam_status)
        cap_row.addStretch()
        layout.addLayout(cap_row)

        # --- Exposure ---
        exp_row = QHBoxLayout()
        exp_row.addWidget(QLabel("Exp (ms):"))
        self._exposure = QDoubleSpinBox()
        self._exposure.setRange(0.1, 60000)
        self._exposure.setDecimals(1)
        self._exposure.setValue(10)
        self._exposure.setSingleStep(1)
        self._exposure.setFixedWidth(80)
        self._exposure.editingFinished.connect(self._set_exposure)
        exp_row.addWidget(self._exposure)
        self._normalize = QCheckBox("Auto-norm")
        self._normalize.setChecked(True)
        exp_row.addWidget(self._normalize)
        exp_row.addStretch()
        layout.addLayout(exp_row)

        # --- ROI row 1: X / Width ---
        roi_row1 = QHBoxLayout()
        roi_row1.addWidget(QLabel("X:"))
        self._roi_x = QSpinBox()
        self._roi_x.setRange(0, 99999)
        roi_row1.addWidget(self._roi_x)
        roi_row1.addWidget(QLabel("W:"))
        self._roi_w = QSpinBox()
        self._roi_w.setRange(1, 99999)
        roi_row1.addWidget(self._roi_w)
        roi_row1.addStretch()
        layout.addLayout(roi_row1)

        # --- ROI row 2: Y / Height ---
        roi_row2 = QHBoxLayout()
        roi_row2.addWidget(QLabel("Y:"))
        self._roi_y = QSpinBox()
        self._roi_y.setRange(0, 99999)
        roi_row2.addWidget(self._roi_y)
        roi_row2.addWidget(QLabel("H:"))
        self._roi_h = QSpinBox()
        self._roi_h.setRange(1, 99999)
        roi_row2.addWidget(self._roi_h)
        self._apply_roi_btn = QPushButton("Apply ROI")
        self._apply_roi_btn.setEnabled(False)
        self._apply_roi_btn.clicked.connect(self._apply_roi)
        roi_row2.addWidget(self._apply_roi_btn)
        layout.addLayout(roi_row2)

        # --- Current ROI label ---
        self._roi_info = QLabel("ROI: --")
        self._roi_info.setWordWrap(True)
        layout.addWidget(self._roi_info)

        # --- Snap row ---
        snap_row = QHBoxLayout()
        self._snap_btn = QPushButton("Snap")
        self._snap_btn.setEnabled(False)
        self._snap_btn.clicked.connect(self._take_snapshot)
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setEnabled(False)
        self._clear_btn.clicked.connect(self._clear_snapshot)
        self._snap_label = QLabel("Snap")
        self._snap_label.setAlignment(Qt.AlignCenter)
        self._snap_label.setMinimumSize(120, 90)
        self._snap_label.setStyleSheet("border: 1px solid #555")
        snap_row.addWidget(self._snap_btn)
        snap_row.addWidget(self._clear_btn)
        snap_row.addWidget(self._snap_label)
        layout.addLayout(snap_row)

        # --- Timer ---
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._update_frame)

        self._fps_timer = QTimer(self)
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.start(1000)

    # ---- public helpers ----

    @property
    def connected(self):
        return self._cam is not None

    @property
    def live_label(self):
        return self._live_label

    @property
    def snap_label(self):
        return self._snap_label

    @property
    def framebuffer(self):
        return self._framebuffer

    @property
    def snapshot(self):
        return self._snapshot

    @property
    def normalize_enabled(self):
        return self._normalize.isChecked()

    # ---- internal ----

    def _init_from_cam(self):
        if self._cam is None:
            return
        try:
            roi = self._cam.get_roi()
            self._roi_x.setValue(roi[0])
            self._roi_y.setValue(roi[2])
            w = roi[1] - roi[0]
            h = roi[3] - roi[2]
            self._roi_w.setValue(w)
            self._roi_h.setValue(h)
            self._roi_info.setText(f"ROI: ({roi[0]},{roi[2]}) {w}×{h}  bin {roi[4]}×{roi[5]}")
            self._exposure.setValue(self._cam.get_exposure() * 1000)
            self._on_connect()
        except Exception as e:
            self._log_msg(f"Init from camera: {e}")

    def _on_connect(self):
        self._connect_btn.setText("Disconnect")
        self._status.setText("Connected")
        self._status.setStyleSheet("color: green")
        self._capture_btn.setEnabled(True)
        self._apply_roi_btn.setEnabled(True)
        self._snap_btn.setEnabled(True)
        self._clear_btn.setEnabled(True)

    def _on_disconnect(self):
        self._connect_btn.setText("Connect")
        self._status.setText("Disconnected")
        self._status.setStyleSheet("color: gray")
        self._capture_btn.setEnabled(False)
        self._apply_roi_btn.setEnabled(False)
        self._snap_btn.setEnabled(False)
        self._clear_btn.setEnabled(False)
        self._capturing = False
        self._capture_btn.setText("Start Capture")
        self._cam_status.setText("")
        self._live_label.setText("No camera")
        self._fps_label.setText("FPS: --")

    def _toggle_connect(self):
        if self._cam is not None:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        try:
            from pylablib.devices import Photometrics
            self._log_msg("Connecting to camera...")
            cam = Photometrics.PvcamCamera()
            cam.open()
            w, h = cam.get_detector_size()
            cam.set_roi(0, w, 0, h, hbin=2, vbin=2)
            try:
                cam.set_trigger_mode(mode="timed", out_mode="global_shutter")
            except Exception:
                pass
            self._cam = cam
            self._log_msg("Camera connected, 2×2 binning set")
            self._init_from_cam()
        except Exception as e:
            self._log_msg(f"Camera connect failed: {e}")
            self._status.setText("Failed")
            self._status.setStyleSheet("color: red")

    def _disconnect(self):
        try:
            if self._cam is not None:
                self._timer.stop()
                self._fps_timer.stop()
                try:
                    self._cam.stop_acquisition()
                except Exception:
                    pass
                self._cam.close()
                self._cam = None
        except Exception as e:
            self._log_msg(f"Disconnect error: {e}")
        self._framebuffer = None
        self._snapshot = None
        self._on_disconnect()
        self._log_msg("Camera disconnected")

    def _toggle_capture(self):
        if self._capturing:
            self._timer.stop()
            try:
                self._cam.stop_acquisition()
            except Exception as e:
                self._log_msg(f"Stop acq: {e}")
            self._capture_btn.setText("Start Capture")
            self._capturing = False
            self._log_msg("Capture stopped")
        else:
            try:
                self._cam.setup_acquisition(mode="sequence")
                self._cam.start_acquisition()
            except Exception as e:
                self._log_msg(f"Start capture failed: {e}")
                return
            self._capture_btn.setText("Stop Capture")
            self._capturing = True
            self._timer.start(0)
            self._log_msg("Capture started")

    def _update_fps(self):
        fps = self._frame_count
        self._fps_label.setText(f"FPS: {fps}")
        self._frame_count = 0

    def _update_frame(self):
        if self._cam is None or not self._capturing:
            return
        try:
            frame = self._cam.read_newest_image()
            if frame is not None:
                self._framebuffer = frame.copy()
                self._display_frame(self._framebuffer, self._live_label)
                self._frame_count += 1
                self._cam_status.setText("Camera: Connected")
                self._timer.start(0)
            else:
                self._timer.start(0)
        except Exception as e:
            self._cam_status.setText("Camera: Error")
            self._log_msg(f"Frame read error: {e}")
            self._timer.start(0)

    def _set_exposure(self):
        if self._cam is None:
            return
        try:
            val_ms = self._exposure.value()
            self._cam.set_exposure(val_ms / 1000)
            self._log_msg(f"Exposure {val_ms} ms")
        except Exception as e:
            self._log_msg(f"Exposure failed: {e}")

    def _apply_roi(self):
        if self._cam is None:
            return
        try:
            x = self._roi_x.value()
            y = self._roi_y.value()
            w = self._roi_w.value()
            h = self._roi_h.value()
            self._cam.stop_acquisition()
            self._cam.set_roi(x, x + w, y, y + h, hbin=2, vbin=2)
            self._cam.setup_acquisition(mode="sequence")
            self._cam.start_acquisition()
            self._cam.wait_for_frame()
            f = self._cam.read_newest_image()
            if f is not None:
                self._framebuffer = f.copy()
            self._roi_info.setText(f"ROI: ({x},{y}) {w}×{h}  bin 2×2")
            self._log_msg(f"ROI set to ({x},{y}) {w}×{h}")
        except Exception as e:
            self._log_msg(f"Apply ROI failed: {e}")

    def _take_snapshot(self):
        if self._framebuffer is None:
            return
        try:
            self._snapshot = self._framebuffer.copy()
            self._display_frame(self._snapshot, self._snap_label)
            self._log_msg("Snapshot taken")
        except Exception as e:
            self._log_msg(f"Snap failed: {e}")

    def _clear_snapshot(self):
        try:
            self._snapshot = None
            self._snap_label.setText("Snap")
            self._log_msg("Snapshot cleared")
        except Exception as e:
            self._log_msg(f"Clear failed: {e}")

    def _display_frame(self, frame, label):
        if frame is None:
            return
        try:
            if self._normalize.isChecked():
                mx = frame.max()
                if mx == 0:
                    display = np.zeros(frame.shape, dtype=np.uint8)
                else:
                    display = ((frame / mx) * 255).astype(np.uint8)
            else:
                display = (frame >> 8).astype(np.uint8)
            h, w = display.shape
            lw, lh = label.width(), label.height()
            if lw > 0 and lh > 0:
                scale = max(1, min(w // lw, h // lh))
                if scale > 1:
                    h2, w2 = h // scale, w // scale
                    display = (
                        display[: h2 * scale, : w2 * scale]
                        .reshape(h2, scale, w2, scale)
                        .mean(axis=(1, 3))
                        .astype(np.uint8)
                    )
                    h, w = display.shape
            q_image = QImage(display.data, w, h, QImage.Format_Grayscale8).copy()
            pixmap = QPixmap.fromImage(q_image).scaled(
                label.width(), label.height(), Qt.KeepAspectRatio
            )
            label.setPixmap(pixmap)
        except Exception as e:
            self._log_msg(f"Display error: {e}")
