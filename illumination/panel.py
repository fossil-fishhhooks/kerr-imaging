import os
import ctypes
from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QSpinBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt
from illumination import IPG


DLP_AVAILABLE = False
_dlp_dll = None


class DLPDevice(ctypes.Structure):
    _fields_ = [
        ("handle", ctypes.c_void_p),
        ("id", ctypes.c_ushort),
        ("ch", ctypes.c_ushort),
    ]


try:
    _DLP_DLL_PATH = r"C:\Users\Arin\PycharmProjects\cameratest\DLP4710EVM_CY.dll"
    _dlp_dll = ctypes.WinDLL(_DLP_DLL_PATH)
    _dlp_dll.OpenWithAutoconnect.argtypes = [ctypes.POINTER(DLPDevice), ctypes.c_char_p]
    _dlp_dll.OpenWithAutoconnect.restype = ctypes.c_int
    _dlp_dll.WriteOperateMode.argtypes = [DLPDevice, ctypes.c_uint8]
    _dlp_dll.WriteOperateMode.restype = ctypes.c_int
    _dlp_dll.WriteExternalVideoSourceFormat.argtypes = [DLPDevice, ctypes.c_uint8]
    _dlp_dll.WriteExternalVideoSourceFormat.restype = ctypes.c_int
    _dlp_dll.WriteDisplaySize.argtypes = [DLPDevice, ctypes.c_uint16, ctypes.c_uint16]
    _dlp_dll.WriteDisplaySize.restype = ctypes.c_int
    _dlp_dll.Close.argtypes = [DLPDevice]
    _dlp_dll.Close.restype = ctypes.c_int
    _dlp_dll.Version.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
    DLP_AVAILABLE = True
except Exception:
    pass


_COLOR_MAP = {"Red": 16711680, "Green": 65280, "Blue": 255}


class LightControlPanel(QGroupBox):
    def __init__(self, log_callback=None, parent=None):
        super().__init__("Light Control", parent)
        self._log = log_callback or (lambda msg: None)
        self._ipg_port = None
        self._dlp_device = None
        self._build_ui()

    def _log_msg(self, msg):
        self._log(f"\n[LIGHT] {msg}")

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- Port row ---
        port_row = QHBoxLayout()
        self._port_combo = QComboBox()
        self._port_combo.addItem("Select a port...")
        for port in IPG.list_serial_ports():
            self._port_combo.addItem(port)
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._toggle_connect)
        self._status = QLabel("Disconnected")
        self._status.setStyleSheet("color: gray")
        port_row.addWidget(self._port_combo)
        port_row.addWidget(self._connect_btn)
        port_row.addWidget(self._status)
        port_row.addStretch()
        layout.addLayout(port_row)

        # --- Arc params row 1: inradius / outradius / color ---
        arc_row1 = QHBoxLayout()
        arc_row1.addWidget(QLabel("In:"))
        self._inradius = QSpinBox()
        self._inradius.setRange(0, 5000)
        self._inradius.setValue(350)
        arc_row1.addWidget(self._inradius)
        arc_row1.addWidget(QLabel("Out:"))
        self._outradius = QSpinBox()
        self._outradius.setRange(0, 5000)
        self._outradius.setValue(400)
        arc_row1.addWidget(self._outradius)
        arc_row1.addWidget(QLabel("Color:"))
        self._color = QComboBox()
        self._color.addItems(["Red", "Green", "Blue"])
        arc_row1.addWidget(self._color)
        layout.addLayout(arc_row1)

        # --- Arc params row 2: startang / endang ---
        arc_row2 = QHBoxLayout()
        arc_row2.addWidget(QLabel("Start:"))
        self._startang = QSpinBox()
        self._startang.setRange(0, 360)
        self._startang.setValue(0)
        arc_row2.addWidget(self._startang)
        arc_row2.addWidget(QLabel("End:"))
        self._endang = QSpinBox()
        self._endang.setRange(0, 360)
        self._endang.setValue(360)
        arc_row2.addWidget(self._endang)
        arc_row2.addStretch()
        layout.addLayout(arc_row2)

        # --- Action buttons ---
        btn_row = QHBoxLayout()
        self._arc_btn = QPushButton("Set Arc")
        self._arc_btn.setEnabled(False)
        self._arc_btn.clicked.connect(self._send_arc)
        self._sleep_btn = QPushButton("Sleep")
        self._sleep_btn.setEnabled(False)
        self._sleep_btn.clicked.connect(self._sleep)
        btn_row.addWidget(self._arc_btn)
        btn_row.addWidget(self._sleep_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _toggle_connect(self):
        if self._ipg_port:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self._port_combo.currentText()
        if port == "Select a port..." or not port:
            return
        try:
            self._log_msg(f"Connecting to {port}...")
            IPG.dumb_login(port)
            self._ipg_port = port
            self._log_msg("Pattern generator running")

            if DLP_AVAILABLE:
                self._dlp_device = DLPDevice()
                acx_path = os.path.join(
                    os.path.dirname(__file__), "dlp.acx"
                )
                ret = _dlp_dll.OpenWithAutoconnect(
                    ctypes.byref(self._dlp_device),
                    ctypes.c_char_p(acx_path.encode()),
                )
                self._log_msg(f"DLP open code {ret}")
                _dlp_dll.WriteOperateMode(self._dlp_device, ctypes.c_uint8(0x00))
                _dlp_dll.WriteExternalVideoSourceFormat(
                    self._dlp_device, ctypes.c_uint8(0x43)
                )
                _dlp_dll.WriteDisplaySize(
                    self._dlp_device, ctypes.c_uint16(1920), ctypes.c_uint16(1080)
                )
                self._log_msg("DLP initialized")
            else:
                self._log_msg("DLP not available (Linux or missing DLL)")

            self._connect_btn.setText("Disconnect")
            self._status.setText(f"Connected: {port}")
            self._status.setStyleSheet("color: green")
            self._arc_btn.setEnabled(True)
            self._sleep_btn.setEnabled(True)
        except Exception as e:
            self._log_msg(f"Connect failed: {e}")
            self._status.setText("Failed")
            self._status.setStyleSheet("color: red")

    def _disconnect(self):
        try:
            if self._dlp_device is not None:
                _dlp_dll.WriteOperateMode(self._dlp_device, ctypes.c_uint8(0xFF))
                _dlp_dll.Close(self._dlp_device)
                self._dlp_device = None
                self._log_msg("DLP standby + closed")
        except Exception as e:
            self._log_msg(f"DLP close error: {e}")
        self._ipg_port = None
        self._connect_btn.setText("Connect")
        self._status.setText("Disconnected")
        self._status.setStyleSheet("color: gray")
        self._arc_btn.setEnabled(False)
        self._sleep_btn.setEnabled(False)
        self._log_msg("Disconnected")

    def _send_arc(self):
        if not self._ipg_port:
            return
        try:
            inr = self._inradius.value()
            outr = self._outradius.value()
            sa = self._startang.value()
            ea = self._endang.value()
            color = _COLOR_MAP[self._color.currentText()]
            cmd = f"arc {inr} {outr} {sa} {ea} {color}\r"
            IPG.send_message(self._ipg_port, cmd)
            self._log_msg(f"Sent: {cmd.strip()}")
        except Exception as e:
            self._log_msg(f"Send arc failed: {e}")

    def _sleep(self):
        try:
            if self._ipg_port:
                IPG.send_message(self._ipg_port, "quit\r")
                self._log_msg("Sent quit to IPG")
            if self._dlp_device is not None:
                _dlp_dll.WriteOperateMode(self._dlp_device, ctypes.c_uint8(0xFF))
                _dlp_dll.Close(self._dlp_device)
                self._dlp_device = None
                self._log_msg("DLP closed")
            self._ipg_port = None
            self._connect_btn.setText("Connect")
            self._status.setText("Sleep")
            self._status.setStyleSheet("color: orange")
            self._arc_btn.setEnabled(False)
            self._sleep_btn.setEnabled(False)
            self._log_msg("System sleeping")
        except Exception as e:
            self._log_msg(f"Sleep failed: {e}")

    @property
    def connected_port(self):
        return self._ipg_port

    @property
    def connected(self):
        return self._ipg_port is not None
