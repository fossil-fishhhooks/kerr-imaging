from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QDoubleSpinBox
)
from PyQt5.QtCore import Qt
from .NanoMax import NanoMax_MDT693B, DeviceError


class PiezoPanel(QGroupBox):
    def __init__(self, log_callback=None, parent=None):
        super().__init__("Piezo Control", parent)
        self._log = log_callback or (lambda msg: None)
        self._device = None
        self._build_ui()
        self._connected = False

    def _log_msg(self, msg):
        self._log(f"\n[PIEZO] {msg}")

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Connect row
        top = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._toggle_connect)
        self._status = QLabel("Disconnected")
        self._status.setStyleSheet("color: gray")
        top.addWidget(self._connect_btn)
        top.addWidget(self._status)
        top.addStretch()
        layout.addLayout(top)

        # Axis rows: label + slider + spinbox + unit
        self._sliders = {}
        self._spins = {}
        for axis, color in [("X", "#e74c3c"), ("Y", "#2ecc71"), ("Z", "#3498db")]:
            row = QHBoxLayout()
            lbl = QLabel(axis)
            lbl.setFixedWidth(16)
            lbl.setStyleSheet(f"font-weight: bold; color: {color}")
            sld = QSlider(Qt.Horizontal)
            sld.setRange(0, 1500)  # 0-150 V, 0.1 V resolution
            sld.setValue(0)
            spn = QDoubleSpinBox()
            spn.setRange(0, 150)
            spn.setDecimals(1)
            spn.setSingleStep(1)
            spn.setValue(0)
            spn.setFixedWidth(72)
            unit = QLabel("V")
            unit.setFixedWidth(12)

            sld.valueChanged.connect(lambda v, s=spn: self._slider_to_spin(s, v / 10))
            spn.valueChanged.connect(lambda v, a=axis: self._spin_changed(a, v))

            row.addWidget(lbl)
            row.addWidget(sld)
            row.addWidget(spn)
            row.addWidget(unit)
            layout.addLayout(row)
            self._sliders[axis] = sld
            self._spins[axis] = spn

        # All axis row
        all_row = QHBoxLayout()
        all_lbl = QLabel("All")
        all_lbl.setFixedWidth(16)
        all_lbl.setStyleSheet("font-weight: bold")
        self._all_slider = QSlider(Qt.Horizontal)
        self._all_slider.setRange(0, 1500)
        self._all_slider.setValue(0)
        self._all_spin = QDoubleSpinBox()
        self._all_spin.setRange(0, 150)
        self._all_spin.setDecimals(1)
        self._all_spin.setSingleStep(1)
        self._all_spin.setValue(0)
        self._all_spin.setFixedWidth(72)
        all_unit = QLabel("V")
        all_unit.setFixedWidth(12)

        self._all_slider.valueChanged.connect(self._on_all_slider)
        self._all_spin.valueChanged.connect(self._on_all_spin)

        all_row.addWidget(all_lbl)
        all_row.addWidget(self._all_slider)
        all_row.addWidget(self._all_spin)
        all_row.addWidget(all_unit)
        layout.addLayout(all_row)

        self._set_enabled(False)

    def _slider_to_spin(self, spin, val):
        spin.blockSignals(True)
        spin.setValue(val)
        spin.blockSignals(False)

    def _spin_changed(self, axis, val):
        self._sliders[axis].blockSignals(True)
        self._sliders[axis].setValue(int(val * 10))
        self._sliders[axis].blockSignals(False)
        if self._connected and self._device:
            try:
                if axis == "X":
                    self._device.xvoltage(val)
                elif axis == "Y":
                    self._device.yvoltage(val)
                elif axis == "Z":
                    self._device.zvoltage(val)
            except Exception as e:
                self._log_msg(f"{axis} set failed: {e}")

    def _set_enabled(self, enabled):
        for axis in ("X", "Y", "Z"):
            self._sliders[axis].setEnabled(enabled)
            self._spins[axis].setEnabled(enabled)
        self._all_slider.setEnabled(enabled)
        self._all_spin.setEnabled(enabled)

    def _on_all_slider(self, v):
        val = v / 10
        self._all_spin.blockSignals(True)
        self._all_spin.setValue(val)
        self._all_spin.blockSignals(False)
        for axis in ("X", "Y", "Z"):
            self._spins[axis].blockSignals(True)
            self._spins[axis].setValue(val)
            self._spins[axis].blockSignals(False)
            self._sliders[axis].blockSignals(True)
            self._sliders[axis].setValue(v)
            self._sliders[axis].blockSignals(False)
        if self._connected and self._device:
            try:
                self._device.allvoltage(val)
            except Exception as e:
                self._log_msg(f"All set failed: {e}")

    def _on_all_spin(self, v):
        self._all_slider.blockSignals(True)
        self._all_slider.setValue(int(v * 10))
        self._all_slider.blockSignals(False)
        for axis in ("X", "Y", "Z"):
            self._spins[axis].blockSignals(True)
            self._spins[axis].setValue(v)
            self._spins[axis].blockSignals(False)
            self._sliders[axis].blockSignals(True)
            self._sliders[axis].setValue(int(v * 10))
            self._sliders[axis].blockSignals(False)
        if self._connected and self._device:
            try:
                self._device.allvoltage(v)
            except Exception as e:
                self._log_msg(f"All set failed: {e}")

    def _toggle_connect(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        from PyQt5.QtWidgets import QInputDialog
        port, ok = QInputDialog.getText(self, "Piezo Port", "Serial port:")
        if not ok or not port:
            return
        try:
            dev = NanoMax_MDT693B(port)
            self._device = dev
            self._connected = True
            self._connect_btn.setText("Disconnect")
            self._status.setText(f"Connected: {port}")
            self._status.setStyleSheet("color: green")
            self._set_enabled(True)
            for axis in ("X", "Y", "Z"):
                try:
                    v = getattr(dev, f"{axis.lower()}voltage")()
                    self._sliders[axis].blockSignals(True)
                    self._spins[axis].blockSignals(True)
                    self._sliders[axis].setValue(int(v * 10))
                    self._spins[axis].setValue(round(v, 1))
                    self._sliders[axis].blockSignals(False)
                    self._spins[axis].blockSignals(False)
                except Exception:
                    pass
            self._log_msg(f"Connected to {port}")
        except DeviceError as e:
            self._log_msg(f"Not an MDT693B: {e}")
        except Exception as e:
            self._log_msg(f"Connection failed: {e}")
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
        self._log_msg("Disconnected")
