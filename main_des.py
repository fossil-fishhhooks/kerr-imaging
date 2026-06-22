import pylablib as pll
from pylablib.devices import Photometrics
import matplotlib.pyplot as plt
import numpy as np
import sys
from PyQt5.QtWidgets import (
    QApplication, QLabel, QMainWindow, QToolBar, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QGroupBox, QTextEdit
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5 import uic
from illumination import IPG
from illumination.dlp import (
    DLP_AVAILABLE, dlp_open, dlp_close, DLPDevice, dlp_set_rgb_current_max, COLOR_RGB,
    dlp_enable_external_pattern_streaming, dlp_disable_external_pattern_streaming,
)
from piezo.panel import PiezoPanel
from lcvr.panel import LCDPanel
import os



def setup():
    try:
        print(f'Cameras: {Photometrics.list_cameras()} \nConnecting to first...')
        # Connect to the camera
        cam = Photometrics.PvcamCamera()
    except Exception as e:
        print("Uh oh! Can't connect to camera. Did you turn it on? Check device manager. If there is a message, kick the empty PCIE port device, and reboot.")
        exit(9)
    cam.open()
    print('Connected \nSetting up...')

    # Set 2x2 hardware binning to reduce frame size 4x (faster DMA copy, less tearing risk)
    try:
        w, h = cam.get_detector_size()
        cam.set_roi(0, w, 0, h, hbin=2, vbin=2)
        print(f'Hardware binning set to 2x2')
    except Exception as e:
        print(f'Could not set 2x2 binning: {e}')

    # Disable rolling shutter if camera supports global shutter output mode
    try:
        cam.set_trigger_mode(mode="timed", out_mode="global_shutter")
        print("Global shutter mode set")
    except Exception:
        print("Global shutter not available, using default shutter mode")

    print(f'Camera frame size: {cam.get_roi()[1]}x{cam.get_roi()[3]}')
    print(f'Camera frame timings: {cam.get_frame_timings()}')

    return cam



def close(camera):
    camera.close()



NoI = 50

cam = setup()
roi = cam.get_roi()
frame_w = (roi[1] - roi[0]) // roi[4]
frame_h = (roi[3] - roi[2]) // roi[5]
framebuffer = np.zeros((frame_h, frame_w), dtype=np.uint16)
framebuffer = cam.grab()[0]


class FramebufferWindow(QMainWindow):
    def __init__(self, cam):
        super().__init__()
        self.cam = cam  # Camera object
        self.framebuffer = self.cam.grab()[0]  # Initial frame
        self.snapshot = None  # Stores the snapshot image

        # Load the UI
        uic.loadUi("main-des.ui", self)  # Load the UI file

        # Access widgets by their objectName


        if self.snap_button is not None:

            self.snap_button.clicked.connect(self.take_snapshot)
        else:
            print("Uh oh! Can't bind to UI button (snap). Check names and things in designer.")
        if self.clear_button is not None:

            self.clear_button.clicked.connect(self.clear_snapshot)
        else:
            print("Uh oh! Can't bind to UI button (clear). Check names and things in designer.")

        self.logtext = ""  # Initialize logtext

        cam.setup_acquisition(mode="sequence")
        cam.start_acquisition()

        # Self-arming single-shot timer (never blocks the UI)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(0)  # Kick off first frame immediately

        self.snapshot = np.zeros(self.framebuffer.shape, dtype=np.uint8)
        height, width = self.snapshot.shape
        q_image = QImage(self.snapshot, width, height, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(q_image).scaled(self.snap_label.width(), self.snap_label.height(), Qt.KeepAspectRatio)
        self.snap_label.setPixmap(pixmap)

        # Capture toggle
        self.capturing = True
        self.capture_button.clicked.connect(self.toggle_capture)

        # IPG / light control setup
        self.ipg_port = None
        self.dlp_device = None

        self.ipg_port_combo.addItem("Select a port...")
        for port in IPG.list_serial_ports():
            self.ipg_port_combo.addItem(port)

        self.ipg_connect_button.clicked.connect(self.connect_ipg)
        self.arc_set_button.clicked.connect(self.send_arc)
        self.ipg_sleep_button.clicked.connect(self.sleep_ipg)
        self.color_combo.currentTextChanged.connect(self._apply_dlp_color)

        # Pattern Streaming toggle button in the Light Control group
        self.stream_btn = QPushButton("Pattern: OFF", self.light_group)
        self.stream_btn.setGeometry(240, 140, 131, 23)
        self.stream_btn.setEnabled(False)
        self.stream_btn.setStyleSheet("background-color: #555; color: #aaa;")
        self.stream_btn.clicked.connect(self._toggle_pattern_streaming)
        self._pattern_streaming_active = False

        # Top toolbar (acts as status bar)
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
        toolbar.setStyleSheet("QToolBar { border: none; spacing: 12px; }")

        self.cam_status_widget = QLabel("Camera: Disconnected")
        self.fps_widget = QLabel("FPS: --")
        self.roi_widget = QLabel("Frame: --")
        self.binning_widget = QLabel("Binning: --")
        self.ipg_status_widget = QLabel("IPG: Disconnected")
        self.piezo_status_widget = QLabel("Piezo: Disconnected")
        self.lcd_status_widget = QLabel("LCVR: Disconnected")

        toolbar.addWidget(self.cam_status_widget)
        toolbar.addWidget(self.fps_widget)
        toolbar.addWidget(self.roi_widget)
        toolbar.addWidget(self.binning_widget)
        toolbar.addSeparator()
        toolbar.addWidget(self.ipg_status_widget)
        toolbar.addSeparator()
        toolbar.addWidget(self.piezo_status_widget)
        toolbar.addSeparator()
        toolbar.addWidget(self.lcd_status_widget)
        self.addToolBar(toolbar)

        # FPS tracking
        self.frame_count = 0
        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(1000)

        # Piezo and LCD panels (right column, below Camera Settings)
        def _log_line(msg):
            self.logtext += msg
            self.log.setText(self.logtext)
            sb = self.log.verticalScrollBar()
            sb.setValue(sb.maximum())

        self.piezo_panel = PiezoPanel(log_callback=_log_line, status_label=self.piezo_status_widget)
        self.piezo_panel.setGeometry(680, 660, 256, 160)
        self.piezo_panel.setParent(self.centralWidget())

        self.lcd_panel = LCDPanel(log_callback=_log_line, status_label=self.lcd_status_widget)
        self.lcd_panel.setGeometry(680, 825, 256, 110)
        self.lcd_panel.setParent(self.centralWidget())

        # Camera settings
        try:
            roi = cam.get_roi()
            self.roi_x_spin.setValue(roi[0])
            self.roi_y_spin.setValue(roi[2])
            w = roi[1] - roi[0]
            h = roi[3] - roi[2]
            self.roi_w_spin.setValue(w)
            self.roi_h_spin.setValue(h)
            self.current_roi_label.setText(
                f"Current ROI: ({roi[0]}, {roi[2]}) → ({roi[1]}, {roi[3]})  [{w}×{h}]"
            )
            self.roi_widget.setText(f"Frame: {w}×{h}")
            hb, vb = roi[4], roi[5]
            self.binning_widget.setText(f"Binning: {hb}×{vb}")
        except Exception as e:
            self.logtext += f"\n[ERROR] Failed to read ROI: {e}"
            self.log.setText(self.logtext)

        try:
            self.exposure_spin.setValue(cam.get_exposure() * 1000)
        except Exception:
            pass

        self.exposure_spin.editingFinished.connect(self.set_exposure)
        self.apply_roi_button.clicked.connect(self.apply_roi)


    def toggle_capture(self):
        if self.capturing:
            self.timer.stop()
            try:
                cam.stop_acquisition()
            except Exception as e:
                self.logtext += f"\n[WARN] Stop acquisition: {e}"
            self.capture_button.setText("Start Capture")
            self.capturing = False
            self.logtext += "\n[INFO] Capture stopped"
        else:
            try:
                cam.setup_acquisition(mode="sequence")
                cam.start_acquisition()
            except Exception as e:
                self.logtext += f"\n[ERROR] Failed to start capture: {e}"
                self.log.setText(self.logtext)
                return
            self.capture_button.setText("Stop Capture")
            self.capturing = True
            self.timer.start(0)
            self.logtext += "\n[INFO] Capture started"
        self.log.setText(self.logtext)


    def set_exposure(self):
        try:
            val_ms = self.exposure_spin.value()
            cam.set_exposure(val_ms / 1000)
            self.logtext += f"\n[INFO] Exposure set to {val_ms} ms"
        except Exception as e:
            self.logtext += f"\n[ERROR] Set exposure failed: {e}"
        self.log.setText(self.logtext)


    def apply_roi(self):
        try:
            x = self.roi_x_spin.value()
            y = self.roi_y_spin.value()
            w = self.roi_w_spin.value()
            h = self.roi_h_spin.value()

            cam.stop_acquisition()
            cam.set_roi(x, x + w, y, y + h, hbin=2, vbin=2)
            cam.setup_acquisition(mode="sequence")
            cam.start_acquisition()

            cam.wait_for_frame()
            self.framebuffer = cam.read_newest_image().copy()

            self.current_roi_label.setText(
                f"Current ROI: ({x}, {y}) → ({x+w}, {y+h})  [{w}×{h}]"
            )
            self.roi_widget.setText(f"Frame: {w}×{h}")
            self.binning_widget.setText(f"Binning: 2×2")
            self.logtext += f"\n[INFO] ROI set to ({x},{y}) {w}×{h}"
        except Exception as e:
            self.logtext += f"\n[ERROR] Apply ROI failed: {e}"
        self.log.setText(self.logtext)


    def update_fps(self):
        fps = self.frame_count
        self.fps_widget.setText(f"FPS: {fps}")
        self.frame_count = 0


    def connect_ipg(self):
        port = self.ipg_port_combo.currentText()
        if port == "Select a port..." or not port:
            return
        try:
            self.logtext += f"\n[IPG] Connecting to {port}..."
            self.log.setText(self.logtext)
            IPG.dumb_login(port)
            self.ipg_port = port
            self.ipg_status_label.setText(f"Connected: {port}")
            self.arc_set_button.setEnabled(True)
            self.ipg_sleep_button.setEnabled(True)
            self.ipg_status_widget.setText("IPG: Connected, Active")
            self.logtext += "\n[IPG] Pattern generator running"

            if DLP_AVAILABLE:
                self.dlp_device = dlp_open()
                self.logtext += "\n[DLP] DLP initialized"
                self._apply_dlp_color()
                self.stream_btn.setEnabled(True)
            else:
                self.logtext += "\n[DLP] DLP not available (Linux or missing DLL)"
        except Exception as e:
            self.logtext += f"\n[ERROR] IPG connect failed: {e}"
            self.ipg_status_label.setText("Connection failed")
            self.ipg_status_widget.setText("IPG: Connection Failed")
        self.log.setText(self.logtext)


    def send_arc(self):
        if not self.ipg_port:
            return
        try:
            inradius = self.inradius_spin.value()
            outradius = self.outradius_spin.value()
            startang = self.startang_spin.value()
            endang = self.endang_spin.value()

            # always white — color is set directly on LEDs via WriteRGBCurrentMax
            cmd = f'arc {inradius} {outradius} {startang} {endang} 16777215\r'
            IPG.send_message(self.ipg_port, cmd)
            self.logtext += f"\n[IPG] Sent: {cmd.strip()}"
        except Exception as e:
            self.logtext += f"\n[ERROR] Send arc failed: {e}"
        self.log.setText(self.logtext)

    def _log_dlp(self, msg):
        self.logtext += f"\n[DLP] {msg}"
        self.log.setText(self.logtext)

    def _apply_dlp_color(self):
        name = self.color_combo.currentText()
        if not name or not self.dlp_device:
            return
        r, g, b = COLOR_RGB[name]
        try:
            dlp_set_rgb_current_max(self.dlp_device, r, g, b, log=self._log_dlp)
            self.logtext += f"\n[DLP] LED color: {name} ({r},{g},{b})"
        except Exception as e:
            self.logtext += f"\n[ERROR] Set DLP color failed: {e}"
        self.log.setText(self.logtext)


    def _toggle_pattern_streaming(self):
        if not self.dlp_device:
            return
        if not self._pattern_streaming_active:
            dlp_enable_external_pattern_streaming(self.dlp_device, log=self._log_dlp)
            self._pattern_streaming_active = True
            self.stream_btn.setText("Pattern: ON")
            self.stream_btn.setStyleSheet("background-color: #2a6; color: #fff;")
            self.logtext += "\n[DLP] External Pattern Streaming ACTIVE"
        else:
            dlp_disable_external_pattern_streaming(self.dlp_device, log=self._log_dlp)
            self._pattern_streaming_active = False
            self.stream_btn.setText("Pattern: OFF")
            self.stream_btn.setStyleSheet("background-color: #555; color: #aaa;")
            self.logtext += "\n[DLP] Back to External Video mode"
        self.log.setText(self.logtext)


    def sleep_ipg(self):
        try:
            if self.ipg_port:
                IPG.send_message(self.ipg_port, "quit\r")
                self.logtext += "\n[IPG] Sent quit command"

            self._pattern_streaming_active = False
            dlp_close(self.dlp_device)
            self.dlp_device = None
            self.stream_btn.setEnabled(False)
            self.stream_btn.setText("Pattern: OFF")
            self.stream_btn.setStyleSheet("background-color: #555; color: #aaa;")

            self.ipg_port = None
            self.ipg_status_label.setText("Disconnected")
            self.arc_set_button.setEnabled(False)
            self.ipg_sleep_button.setEnabled(False)
            self.ipg_status_widget.setText("IPG: Connected, Sleep (reconnect to reactivate)")
            self.logtext += "\n[IPG] System in sleep mode"
        except Exception as e:
            self.logtext += f"\n[ERROR] Sleep failed: {e}"
        self.log.setText(self.logtext)


    def update_frame(self):
        try:
            frame = cam.read_newest_image()
            if frame is not None:
                self.framebuffer = frame.copy()
                self.display_frame(self.framebuffer, self.live_label)
                self.frame_count += 1
                self.cam_status_widget.setText("Camera: Connected")

                scrollbar = self.log.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                if self.capturing:
                    self.timer.start(0)
            else:
                if self.capturing:
                    self.timer.start(0)
        except Exception as e:
            self.cam_status_widget.setText("Camera: Disconnected")
            self.logtext += f"\n[ERROR] read_newest_image failed: {e}"
            self.log.setText(self.logtext)
            if self.capturing:
                self.timer.start(0)

    def take_snapshot(self):
        try:
            #print("Taking snapshot...")
            self.logtext += "\n[INFO] Snap pressed"
            self.log.setText(self.logtext)
            self.snapshot = self.framebuffer.copy()
            self.display_frame(self.snapshot, self.snap_label)
            self.logtext += "\n[INFO] Drew snap"
            self.log.setText(self.logtext)
        except Exception as e:

            self.logtext += "\n[ERROR] " + str(e)
            self.log.setText(self.logtext)

    def clear_snapshot(self):
        try:
            #print("Clearing snapshot...")
            self.logtext += "\n[INFO] Clear pressed"
            self.log.setText(self.logtext)
            self.snapshot = np.zeros(self.framebuffer.shape, dtype=np.uint8)
            height, width = self.snapshot.shape
            q_image = QImage(self.snapshot, width, height, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_image).scaled(self.snap_label.width(), self.snap_label.height(), Qt.KeepAspectRatio)
            self.snap_label.setPixmap(pixmap)
            self.logtext += "\n[INFO] Snap cleared"
            self.log.setText(self.logtext)
        except Exception as e:

            self.logtext += "\n[ERROR] " + str(e)
            self.log.setText(self.logtext)

    def display_frame(self, frame, label):
        try:
            if frame is None:
                return
            if self.normalize_check.isChecked():
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
                scale = max(1, min(w // lw, h // lh)) if lw > 0 and lh > 0 else 1
                if scale > 1:
                    h2, w2 = h // scale, w // scale
                    display = display[:h2*scale, :w2*scale].reshape(h2, scale, w2, scale).mean(axis=(1, 3)).astype(np.uint8)
                    h, w = display.shape
            q_image = QImage(display.data, w, h, QImage.Format_Grayscale8).copy()
            pixmap = QPixmap.fromImage(q_image).scaled(label.width(), label.height(), Qt.KeepAspectRatio)
            label.setPixmap(pixmap)
        except Exception as e:
            self.logtext += "\n[ERROR] display_frame: " + str(e)
            self.log.setText(self.logtext)


if __name__ == "__main__":


    app = QApplication(sys.argv)
    window = FramebufferWindow(cam)
    window.show()
    sys.exit(app.exec_())

