from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from .d5020 import D5020, D5020Error


_TOLERANCE = 0.02


class LCDPanel(QGroupBox):

    _connected_changed = pyqtSignal(bool)

    def __init__(self, log_callback=None, status_label=None, parent=None):
        super().__init__("LCVR Retardance", parent)
        self._log = log_callback or (lambda msg: None)
        self._status_label = status_label
        self._device = None
        self._connected = False
        self._build_ui()

    def _log_msg(self, msg):
        self._log(f"\n[LCD] {msg}")

    def _build_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._toggle_connect)
        self._status = QLabel("Disconnected")
        self._status.setStyleSheet("color: gray")
        top.addWidget(self._connect_btn)
        top.addWidget(self._status)
        top.addStretch()
        layout.addLayout(top)

        self._sliders = {}
        self._spins = {}
        for port in (0, 1):
            row = QHBoxLayout()
            lbl = QLabel(f"Port {port}")
            lbl.setFixedWidth(42)
            lbl.setStyleSheet("font-weight: bold")
            sld = QSlider(Qt.Horizontal)
            sld.setRange(0, 640)
            sld.setValue(0)
            spn = QDoubleSpinBox()
            spn.setRange(0, 0.64)
            spn.setDecimals(3)
            spn.setSingleStep(0.01)
            spn.setValue(0)

            sld.valueChanged.connect(lambda v, s=spn: self._slider_to_spin(s, v / 1000))
            spn.valueChanged.connect(lambda v, p=port: self._spin_changed(p, v))

            row.addWidget(lbl)
            row.addWidget(sld)
            row.addWidget(spn)
            layout.addLayout(row)
            self._sliders[port] = sld
            self._spins[port] = spn

        self._set_enabled(False)

    def _set_enabled(self, enabled):
        for port in (0, 1):
            self._sliders[port].setEnabled(enabled)
            self._spins[port].setEnabled(enabled)

    def _slider_to_spin(self, spin, val):
        spin.blockSignals(True)
        spin.setValue(val)
        spin.blockSignals(False)

    def _spin_changed(self, port, val):
        self._sliders[port].blockSignals(True)
        self._sliders[port].setValue(int(round(val * 1000)))
        self._sliders[port].blockSignals(False)
        if self._connected and self._device:
            try:
                self._device.retardance(port, val)
            except Exception as e:
                self._log_msg(f"Port {port} set failed: {e}")

    def _toggle_connect(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        try:
            dev = D5020()
            dev.open()
            self._device = dev
            self._connected = True
            self._connect_btn.setText("Disconnect")
            self._status.setText("Connected")
            self._status.setStyleSheet("color: green")
            self._set_enabled(True)
            for port in (0, 1):
                try:
                    v = dev.retardance(port)
                    self._spins[port].blockSignals(True)
                    self._sliders[port].blockSignals(True)
                    self._spins[port].setValue(round(v, 3))
                    self._sliders[port].setValue(int(round(v * 1000)))
                    self._spins[port].blockSignals(False)
                    self._sliders[port].blockSignals(False)
                except Exception:
                    pass
            if self._status_label:
                self._status_label.setText("LCVR: Connected")
            self._connected_changed.emit(True)
            self._log_msg("LCD connected")
        except D5020Error as e:
            self._log_msg(f"LCD connection failed: {e}")
            self._status.setText("Failed")
            self._status.setStyleSheet("color: red")
        except Exception as e:
            self._log_msg(f"LCD connection error: {e}")
            self._status.setText("Failed")
            self._status.setStyleSheet("color: red")

    def _disconnect(self):
        try:
            if self._device:
                self._device.close()
        except Exception as e:
            self._log_msg(f"Close error: {e}")
        self._device = None
        self._connected = False
        self._connect_btn.setText("Connect")
        self._status.setText("Disconnected")
        self._status.setStyleSheet("color: gray")
        self._set_enabled(False)
        if self._status_label:
            self._status_label.setText("LCVR: Disconnected")
        self._connected_changed.emit(False)
        self._log_msg("LCD disconnected")
