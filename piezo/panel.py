import queue
import time
import threading
from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QObject
from .NanoMax import NanoMax_MDT693B, DeviceError


class _PiezoPoller(QObject):
    results = pyqtSignal(object)

    def __init__(self, device, interval=0.5):
        super().__init__()
        self._device = device
        self._interval = interval
        self._running = False
        self._cmds = queue.Queue()

    def start(self):
        self._running = True
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def set_voltage(self, axis, val):
        self._cmds.put(("axis", axis, val))

    def set_all(self, val):
        self._cmds.put(("all", val))

    def poll_now(self):
        try:
            vals = {}
            for axis in ("X", "Y", "Z"):
                vals[axis] = getattr(self._device, f"{axis.lower()}voltage")()
            self.results.emit(vals)
        except Exception:
            pass

    def _run(self):
        while self._running:
            for _ in range(50):
                if not self._running:
                    return
                try:
                    cmd = self._cmds.get_nowait()
                    if cmd[0] == "axis":
                        _, axis, val = cmd
                        getattr(self._device, f"{axis.lower()}voltage")(val)
                    elif cmd[0] == "all":
                        _, val = cmd
                        self._device.allvoltage(val)
                except queue.Empty:
                    break
                except Exception:
                    pass
            try:
                vals = {}
                for axis in ("X", "Y", "Z"):
                    vals[axis] = getattr(self._device, f"{axis.lower()}voltage")()
                self.results.emit(vals)
            except Exception:
                pass
            for _ in range(max(1, int(self._interval * 100))):
                if not self._running:
                    return
                time.sleep(0.01)


class PiezoPanel(QGroupBox):

    _connected_changed = pyqtSignal(bool)

    def __init__(self, log_callback=None, status_label=None, parent=None):
        super().__init__("Piezo Control", parent)
        self._log = log_callback or (lambda msg: None)
        self._status_label = status_label
        self._device = None
        self._poller = None
        self._build_ui()
        self._connected = False

    def _log_msg(self, msg):
        self._log(f"\n[PIEZO] {msg}")

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
        self._actuals = {}
        for axis, color in [("X", "#e74c3c"), ("Y", "#2ecc71"), ("Z", "#3498db")]:
            row = QHBoxLayout()
            lbl = QLabel(axis)
            lbl.setFixedWidth(16)
            lbl.setStyleSheet(f"font-weight: bold; color: {color}")
            sld = QSlider(Qt.Horizontal)
            sld.setRange(0, 1500)
            sld.setValue(0)
            spn = QDoubleSpinBox()
            spn.setRange(0, 150)
            spn.setDecimals(1)
            spn.setSingleStep(1)
            spn.setValue(0)
            spn.setFixedWidth(68)
            unit = QLabel("V")
            unit.setFixedWidth(10)
            act = QLabel("—")
            act.setFixedWidth(54)
            act.setStyleSheet("color: gray")

            sld.valueChanged.connect(lambda v, s=spn: self._slider_to_spin(s, v / 10))
            spn.valueChanged.connect(lambda v, a=axis: self._spin_changed(a, v))

            row.addWidget(lbl)
            row.addWidget(sld)
            row.addWidget(spn)
            row.addWidget(unit)
            row.addWidget(act)
            layout.addLayout(row)
            self._sliders[axis] = sld
            self._spins[axis] = spn
            self._actuals[axis] = act

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
        self._all_spin.setFixedWidth(68)
        all_unit = QLabel("V")
        all_unit.setFixedWidth(10)
        self._live_indicator = QLabel("")
        self._live_indicator.setFixedWidth(16)

        self._all_slider.valueChanged.connect(self._on_all_slider)
        self._all_spin.valueChanged.connect(self._on_all_spin)

        all_row.addWidget(all_lbl)
        all_row.addWidget(self._all_slider)
        all_row.addWidget(self._all_spin)
        all_row.addWidget(all_unit)
        all_row.addWidget(self._live_indicator)
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
        if self._connected and self._poller:
            self._poller.set_voltage(axis, val)

    @pyqtSlot(object)
    def _on_actual(self, vals):
        for axis in ("X", "Y", "Z"):
            v = vals.get(axis)
            if v is not None:
                self._actuals[axis].setText(f"{v:>5.1f} V")
                self._actuals[axis].setStyleSheet("color: #888")
            else:
                self._actuals[axis].setText("?.?")

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
        if self._connected and self._poller:
            self._poller.set_all(val)

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
        if self._connected and self._poller:
            self._poller.set_all(v)

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
            self._live_indicator.setText("↻")
            self._live_indicator.setStyleSheet("color: #4a4")
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
            self._poller = _PiezoPoller(dev, interval=0.5)
            self._poller.results.connect(self._on_actual)
            self._poller.poll_now()
            self._poller.start()
            if self._status_label:
                self._status_label.setText("Piezo: Connected")
                self._status_label.setStyleSheet("color: green")
            self._connected_changed.emit(True)
            self._log_msg(f"Connected to {port}")
        except DeviceError as e:
            self._log_msg(f"Not an MDT693B: {e}")
        except Exception as e:
            self._log_msg(f"Connection failed: {e}")
            self._status.setText("Failed")
            self._status.setStyleSheet("color: red")

    def _disconnect(self):
        if self._poller:
            self._poller.stop()
            self._poller = None
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
        self._live_indicator.setText("")
        self._set_enabled(False)
        for axis in ("X", "Y", "Z"):
            self._actuals[axis].setText("—")
        if self._status_label:
            self._status_label.setText("Piezo: Disconnected")
            self._status_label.setStyleSheet("color: gray")
        self._connected_changed.emit(False)
        self._log_msg("Disconnected")
