from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal


class LCDPanel(QGroupBox):

    _connected_changed = pyqtSignal(bool)

    def __init__(self, log_callback=None, status_label=None, parent=None):
        super().__init__("LCD Retardance", parent)
        self._log = log_callback or (lambda msg: None)
        self._status_label = status_label
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
            sld.setRange(0, 1000)
            sld.setValue(0)
            spn = QDoubleSpinBox()
            spn.setRange(0, 10)
            spn.setDecimals(2)
            spn.setSingleStep(0.1)
            spn.setValue(0)
            spn.setFixedWidth(72)

            sld.valueChanged.connect(lambda v, s=spn: self._slider_to_spin(s, v / 100))
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
        self._sliders[port].setValue(int(val * 100))
        self._sliders[port].blockSignals(False)
        if self._connected:
            self._on_ret_change(port, val)

    def _on_ret_change(self, port, val):
        pass

    def _toggle_connect(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        self._log_msg("LCD hardware connection not yet implemented")
        self._connected = True
        self._connect_btn.setText("Disconnect")
        self._status.setText("Connected (mock)")
        self._status.setStyleSheet("color: green")
        self._set_enabled(True)
        if self._status_label:
            self._status_label.setText("LCD: Connected (mock)")
        self._connected_changed.emit(True)

    def _disconnect(self):
        self._connected = False
        self._connect_btn.setText("Connect")
        self._status.setText("Disconnected")
        self._status.setStyleSheet("color: gray")
        self._set_enabled(False)
        if self._status_label:
            self._status_label.setText("LCD: Disconnected")
        self._connected_changed.emit(False)
        self._log_msg("Disconnected")
