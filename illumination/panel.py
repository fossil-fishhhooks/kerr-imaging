import os
from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QSpinBox
)
from PyQt5.QtCore import Qt
from illumination import IPG
from illumination.dlp import DLP_AVAILABLE, dlp_open, dlp_close, dlp_set_rgb_current_max, COLOR_MAP, COLOR_RGB


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
        self._color.currentTextChanged.connect(self._apply_color)
        arc_row1.addWidget(self._color)
        layout.addLayout(arc_row1)

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
        arc_row2.addStretch()
        layout.addLayout(arc_row2)

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
                self._dlp_device = dlp_open()
                self._log_msg("DLP initialized")
                self._apply_color()
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
            dlp_close(self._dlp_device)
            self._dlp_device = None
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
            # always white — color is set directly on LEDs via WriteRGBCurrentMax
            cmd = f"arc {inr} {outr} {sa} {ea} 16777215\r"
            IPG.send_message(self._ipg_port, cmd)
            self._log_msg(f"Sent: {cmd.strip()}")
        except Exception as e:
            self._log_msg(f"Send arc failed: {e}")

    def _apply_color(self):
        name = self._color.currentText()
        if not name or not self._dlp_device:
            return
        r, g, b = COLOR_RGB[name]
        try:
            dlp_set_rgb_current_max(self._dlp_device, r, g, b)
            self._log_msg(f"LED color: {name} ({r},{g},{b}) max current")
        except Exception as e:
            self._log_msg(f"Set color failed: {e}")

    def _sleep(self):
        try:
            if self._ipg_port:
                IPG.send_message(self._ipg_port, "quit\r")
                self._log_msg("Sent quit to IPG")
            dlp_close(self._dlp_device)
            self._dlp_device = None
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
