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
import IPG
import ctypes

# Optional DLP DLL (Windows only, graceful fallback on Linux)
DLP_AVAILABLE = False
dlp_dll = None

class DLPDevice(ctypes.Structure):
    _fields_ = [
        ("handle", ctypes.c_void_p),
        ("id", ctypes.c_ushort),
        ("ch", ctypes.c_ushort)
    ]

try:
    DLP_DLL_PATH = r"C:\Users\Arin\PycharmProjects\cameratest\DLP4710EVM_CY.dll"
    dlp_dll = ctypes.WinDLL(DLP_DLL_PATH)
    dlp_dll.OpenWithAutoconnect.argtypes = [ctypes.POINTER(DLPDevice), ctypes.c_char_p]
    dlp_dll.OpenWithAutoconnect.restype = ctypes.c_int
    dlp_dll.WriteOperateMode.argtypes = [DLPDevice, ctypes.c_uint8]
    dlp_dll.WriteOperateMode.restype = ctypes.c_int
    dlp_dll.WriteExternalVideoSourceFormat.argtypes = [DLPDevice, ctypes.c_uint8]
    dlp_dll.WriteExternalVideoSourceFormat.restype = ctypes.c_int
    dlp_dll.WriteDisplaySize.argtypes = [DLPDevice, ctypes.c_uint16, ctypes.c_uint16]
    dlp_dll.WriteDisplaySize.restype = ctypes.c_int
    dlp_dll.Close.argtypes = [DLPDevice]
    dlp_dll.Close.restype = ctypes.c_int
    dlp_dll.Version.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
    DLP_AVAILABLE = True
    print(f"[DLP] DLP4710EVM_CY.dll loaded")
except Exception:
    print("[DLP] DLP4710EVM_CY.dll not available — DLP control disabled")



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
    #cam.set_roi(0,18,0,18,1,1)
    print(f'Camera frame size: {cam.get_roi()[1]}x{cam.get_roi()[3]}')
    print(f'Camera frame timings: {cam.get_frame_timings()}')
    # Set exposure time (in milliseconds)
    #cam.set_exposure(10E-3)  # set 10ms exposure

    #cam.start_acquisition(mode='snap', nframes=1)


    return cam



def close(camera):
    camera.close()



NoI = 50

cam = setup()
framebuffer = np.zeros((2960, 5056), dtype=np.uint16)
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

        # Timer for live update
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(1000 // 50)  # 50 FPS MAXIMUM

        self.snapshot = np.zeros((2960, 5056), dtype=np.uint8)
        height, width = self.snapshot.shape
        q_image = QImage(self.snapshot, width, height, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(q_image).scaled(self.snap_label.width(), self.snap_label.height(), Qt.KeepAspectRatio)
        self.snap_label.setPixmap(pixmap)

        cam.setup_acquisition(mode="sequence")
        cam.start_acquisition()

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

        # Top toolbar (acts as status bar)
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
        toolbar.setStyleSheet("QToolBar { border: none; spacing: 12px; }")

        self.cam_status_widget = QLabel("Camera: Disconnected")
        self.fps_widget = QLabel("FPS: --")
        self.roi_widget = QLabel("Frame: --")
        self.ipg_status_widget = QLabel("IPG: Disconnected")

        toolbar.addWidget(self.cam_status_widget)
        toolbar.addWidget(self.fps_widget)
        toolbar.addWidget(self.roi_widget)
        toolbar.addSeparator()
        toolbar.addWidget(self.ipg_status_widget)
        self.addToolBar(toolbar)

        # FPS tracking
        self.frame_count = 0
        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(1000)

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
            except Exception:
                pass
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
            self.timer.start(1000 // 50)
            self.capture_button.setText("Stop Capture")
            self.capturing = True
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
            cam.set_roi(x, x + w, y, y + h, 1, 1)
            cam.setup_acquisition(mode="sequence")
            cam.start_acquisition()

            cam.wait_for_frame()
            self.framebuffer = cam.read_oldest_image()

            self.current_roi_label.setText(
                f"Current ROI: ({x}, {y}) → ({x+w}, {y+h})  [{w}×{h}]"
            )
            self.roi_widget.setText(f"Frame: {w}×{h}")
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
                self.dlp_device = DLPDevice()
                ret = dlp_dll.OpenWithAutoconnect(
                    ctypes.byref(self.dlp_device), ctypes.c_char_p(b"dlp.acx")
                )
                self.logtext += f"\n[DLP] Open with code {ret}"
                dlp_dll.WriteOperateMode(self.dlp_device, ctypes.c_uint8(0x00))
                dlp_dll.WriteExternalVideoSourceFormat(self.dlp_device, ctypes.c_uint8(0x43))
                dlp_dll.WriteDisplaySize(self.dlp_device, ctypes.c_uint16(1920), ctypes.c_uint16(1080))
                self.logtext += "\n[DLP] DLP initialized"
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

            color_map = {"Red": 16711680, "Green": 65280, "Blue": 255}
            color = color_map[self.color_combo.currentText()]

            cmd = f'arc {inradius} {outradius} {startang} {endang} {color}\r'
            IPG.send_message(self.ipg_port, cmd)
            self.logtext += f"\n[IPG] Sent: {cmd.strip()}"
        except Exception as e:
            self.logtext += f"\n[ERROR] Send arc failed: {e}"
        self.log.setText(self.logtext)


    def sleep_ipg(self):
        try:
            if self.ipg_port:
                IPG.send_message(self.ipg_port, "quit\r")
                self.logtext += "\n[IPG] Sent quit command"

            if self.dlp_device is not None:
                ret = dlp_dll.WriteOperateMode(self.dlp_device, ctypes.c_uint8(0xFF))
                self.logtext += f"\n[DLP] Standby set with code {ret}"
                dlp_dll.Close(self.dlp_device)
                self.logtext += "\n[DLP] DLP closed"
                self.dlp_device = None

            self.ipg_port = None
            self.ipg_status_label.setText("Disconnected")
            self.arc_set_button.setEnabled(False)
            self.ipg_sleep_button.setEnabled(False)
            self.ipg_status_widget.setText("IPG: Connected, Sleep")
            self.logtext += "\n[IPG] System in sleep mode"
        except Exception as e:
            self.logtext += f"\n[ERROR] Sleep failed: {e}"
        self.log.setText(self.logtext)


    def update_frame(self):
        try:
            #print("Updating frame...")
            cam.wait_for_frame()  # Wait for the next available frame, not necessary, but keep updating why not
            self.framebuffer = cam.read_oldest_image()  # Get the oldest image
            self.display_frame(self.framebuffer, self.live_label)
            self.frame_count += 1

            self.cam_status_widget.setText("Camera: Connected")

            scrollbar = self.log.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            self.cam_status_widget.setText("Camera: Disconnected")

            self.logtext += "\n[ERROR] " + str(e)
            self.log.setText(self.logtext)

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
            self.snapshot = np.zeros((2960, 5056), dtype=np.uint8)
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
        """Converts and displays a frame in a QLabel."""
        try:
            if frame is None:
                return
            mx = frame.max()
            if mx == 0:
                normalized_frame = np.zeros(frame.shape, dtype=np.uint8)
            else:
                normalized_frame = ((frame / mx) * 255).astype(np.uint8)
            height, width = normalized_frame.shape
            q_image = QImage(normalized_frame.data, width, height, QImage.Format_Grayscale8)
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

