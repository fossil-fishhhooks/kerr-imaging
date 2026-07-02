# Meadowlark Optics D5020 Python Wrapper

import os
import sys
import threading
from ctypes import *
from ctypes.wintypes import *

from .i_suck_at_math import calculate_correct_delta2

def makecmd (cmdstr):
#This function converts a command string to a byte array and adds the carriage return character to the end.
    cmdlen = len(cmdstr) + 1 #set up length
    cmdarr = c_byte * cmdlen #and command byte array
    cmdtosend = cmdarr()
    chartmp = 0  #temp char variable
    for x in range(cmdlen - 1):#go through command string
        chartmp = ord(cmdstr[x]) #and get current character and convert to byte
        cmdtosend[x] = chartmp #then put it as the current character in the array.
    cmdtosend[cmdlen-1] = 13 #add CR
    return (cmdtosend,cmdlen) #return the command array and length.

def buffer2str (cmdstatus):
#This function converts a char array to a string, finishing when it sees a carriage return.
    responsestr = "" #make empty string
    for x in range (64): #Go through response buffer.
        if cmdstatus[x] == 13: #if found carriage return
            break #function is done
        responsestr = responsestr + chr(cmdstatus[x]) #otherwise add current character to string.
    return responsestr #return the response string


class D5020Error(Exception):
    pass


_NATIVE_WAVELENGTH = 633.0


class D5020:
    def __init__(self, dll_path=None, port=None, model=None, wavelength=None):
        if dll_path is None:
            dll_path = r"C:\Users\Arin\PycharmProjects\cameratest\usbdrvd"
        self.mlousb = WinDLL(dll_path)
        self.mlousb.USBDRVD_OpenDevice.restype = HANDLE
        self.mlousb.USBDRVD_InterruptWrite.argtypes = [HANDLE, c_uint, POINTER(c_byte), c_uint]
        self.mlousb.USBDRVD_InterruptRead.argtypes = [HANDLE, c_uint, POINTER(c_byte), c_uint]
        self.mlousb.USBDRVD_CloseDevice.argtypes = [HANDLE]
        self.usb_pid = c_uint(5020)
        self.flagsandattrs = c_uint(1073741824)
        self.devhandle = None
        self._cal_raw = {}       # port -> [(mV, nm_at_633), ...]  (never changes)
        self._cal = {}           # port -> [(mV, nm_at_curr_wl), ...]  (rebuilt by set_wavelength)
        self._wavelength = None  # current wavelength in nm
        if model is not None:
            self.load_calibration(port if port is not None else 0, model, wavelength)

    def load_calibration(self, port, model, wavelength=None):
        """Load calibration from file in lcvr/calib/<model>.

        File format: tab-separated columns (mV, nm, waves).
        Stores raw (mV, nm_at_633) pairs and builds the active calibration
        for the requested wavelength (defaults to the calibration's native 633 nm).
        """
        path = os.path.join(os.path.dirname(__file__), "calib", str(model))
        if not os.path.exists(path):
            raise FileNotFoundError(f"Calibration file not found: {path}")
        raw = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    mv = float(parts[0])
                    nm = float(parts[1])
                    raw.append((mv, nm))
        if not raw:
            raise ValueError(f"No calibration data parsed from {path}")
        self._cal_raw[port] = sorted(raw, key=lambda p: p[0])
        wl = wavelength if wavelength is not None else _NATIVE_WAVELENGTH
        self._set_port_wavelength(port, wl)

    def set_calibration(self, port, table):
        """Set voltage(mV)->retardance(nm) calibration lookup table for a port.

        *table* is a list of (voltage_mV, retardance_nm) pairs sorted by voltage.
        This stores both the raw (assumed at 633 nm) and active calibration.
        """
        t = sorted(table, key=lambda p: p[0])
        self._cal_raw[port] = list(t)
        self._cal[port] = list(t)
        if self._wavelength is None:
            self._wavelength = _NATIVE_WAVELENGTH

    @staticmethod
    def _interp(table, x):
        if x <= table[0][0]:
            return table[0][1]
        if x >= table[-1][0]:
            return table[-1][1]
        for (x0, y0), (x1, y1) in zip(table, table[1:]):
            if x0 <= x <= x1:
                t = (x - x0) / (x1 - x0)
                return y0 + (y1 - y0) * t
        return table[-1][1]

    @staticmethod
    def _rinterp(table, y):
        """Reverse interpolation: find x for a given y (monotonically decreasing)."""
        if y >= table[0][1]:
            return table[0][0]
        if y <= table[-1][1]:
            return table[-1][0]
        for (x0, y0), (x1, y1) in zip(table, table[1:]):
            if y0 >= y >= y1:
                t = (y - y0) / (y1 - y0)
                return int(round(x0 + (x1 - x0) * t))
        return int(round(table[-1][0]))

    def set_wavelength(self, new_wavelength):
        """Recompute internal calibration for every port to *new_wavelength* nm.

        Uses shift_wavelength() from i_suck_at_math on each raw (mV, nm_at_633) point.
        """
        for port in list(self._cal_raw):
            self._set_port_wavelength(port, new_wavelength)
        self._wavelength = new_wavelength

    def _set_port_wavelength(self, port, wl):
        raw = self._cal_raw.get(port)
        if raw is None:
            raise D5020Error(f"No raw calibration for port {port}")
        if wl == _NATIVE_WAVELENGTH:
            self._cal[port] = list(raw)
        else:
            shifted = []
            for mv, nm_633 in raw:
                nm_new = calculate_correct_delta2(_NATIVE_WAVELENGTH, nm_633, wl)
                shifted.append((mv, nm_new))
            self._cal[port] = sorted(shifted, key=lambda p: p[0])
        self._wavelength = wl

    def _get_cal_nm(self, port):
        cal = self._cal.get(port)
        if cal is None:
            raise D5020Error(f"No calibration loaded for port {port}")
        return cal

    def _voltage_to_retardance_nm(self, port, mv):
        return self._interp(self._get_cal_nm(port), mv)

    def _retardance_nm_to_voltage(self, port, nm):
        return self._rinterp(self._get_cal_nm(port), max(0.0, nm))

    def _curr_wavelength(self):
        return self._wavelength if self._wavelength is not None else _NATIVE_WAVELENGTH

    def device_count(self):
        return self.mlousb.USBDRVD_GetDevCount(self.usb_pid)

    def open(self, dev_number=1):
        if self.devhandle is not None:
            return
        self.devhandle = self.mlousb.USBDRVD_OpenDevice(c_uint(dev_number), self.flagsandattrs, self.usb_pid)

    def close(self):
        if self.devhandle:
            self.mlousb.USBDRVD_CloseDevice(self.devhandle)
            self.devhandle = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _cmd(self, command, timeout=None):
        if not self.devhandle:
            raise D5020Error("Device not opened")
        (cmdtosend,cmdlen) = makecmd(command)
        cmdptr = (c_byte * len(cmdtosend))(*cmdtosend)
        self.mlousb.USBDRVD_InterruptWrite(self.devhandle, c_uint(1), cmdptr, cmdlen)
        usbbuffer = c_byte * 64
        cmdstatus = usbbuffer()
        if timeout is None:
            self.mlousb.USBDRVD_InterruptRead(self.devhandle, c_uint(0), cmdstatus, c_uint(64))
        else:
            exc = []
            def _read():
                try:
                    self.mlousb.USBDRVD_InterruptRead(self.devhandle, c_uint(0), cmdstatus, c_uint(64))
                except Exception as e:
                    exc.append(e)
            t = threading.Thread(target=_read, daemon=True)
            t.start()
            t.join(timeout)
            if t.is_alive():
                raise D5020Error(f"Timeout after {timeout}s: {command}")
            if exc:
                raise exc[0]
        return buffer2str(cmdstatus)

    def version(self, timeout=None):
        return self._cmd("ver:?", timeout=timeout)

    def retardance(self, port, value=None, timeout=2):
        """Get/set retardance in waves on a channel.

        Port 0 -> channel 1, Port 1 -> channel 2.
        Uses per-port calibration at the currently-set wavelength.
        """
        if value is None:
            nm = self._get_retardance_nm(port, timeout)
            return nm / self._curr_wavelength()
        self.set_retardance_waves(port, value, timeout)

    def _get_retardance_nm(self, port, timeout=2):
        channel = port + 1
        raw = self._cmd(f"ld:{channel},?", timeout=timeout)
        mv = self._parse_float(raw)
        return self._voltage_to_retardance_nm(port, mv)

    def set_retardance_nm(self, port, value, timeout=2):
        """Set retardance in nanometres on a channel."""
        channel = port + 1
        mv = self._retardance_nm_to_voltage(port, max(0.0, value))
        self._cmd(f"ld:{channel},{mv}", timeout=timeout)

    def set_retardance_waves(self, port, value, timeout=2):
        """Set retardance in waves on a channel."""
        nm = max(0.0, value) * self._curr_wavelength()
        self.set_retardance_nm(port, nm, timeout)

    def temperature(self, channel=1, timeout=None):
        raw = self._cmd(f"tmp:{channel},?", timeout=timeout)
        return self._parse_float(raw)

    def serial_number(self, timeout=None):
        return self._cmd("rsn:?", timeout=timeout)

    @staticmethod
    def _parse_float(raw):
        for tok in raw.replace(",", " ").split():
            try:
                return float(tok)
            except ValueError:
                continue
        return 0.0


if __name__ == "__main__":
    # Use the same proven pattern as D5020Example.py
    dll = r"C:\Users\Arin\PycharmProjects\cameratest\usbdrvd"
    mlousb = WinDLL(dll)
    mlousb.USBDRVD_OpenDevice.restype = HANDLE
    mlousb.USBDRVD_InterruptWrite.argtypes = [HANDLE, c_uint, POINTER(c_byte), c_uint]
    mlousb.USBDRVD_InterruptRead.argtypes = [HANDLE, c_uint, POINTER(c_byte), c_uint]
    mlousb.USBDRVD_CloseDevice.argtypes = [HANDLE]

    usb_pid = c_uint(5020)
    flagsandattrs = c_uint(1073741824)
    writepipe = c_uint(1)
    readpipe = c_uint(0)
    bufferlen = c_uint(64)

    n = mlousb.USBDRVD_GetDevCount(usb_pid)
    if n == 0:
        print("No Devices Found.")
        sys.exit(1)
    print(f"Found {n} device(s).\n")

    devhandle = mlousb.USBDRVD_OpenDevice(c_uint(1), flagsandattrs, usb_pid)
    print("Device opened.")

    # wrap in class API so we get calibration-aware retardance
    dev = D5020.__new__(D5020)
    dev.mlousb = mlousb
    dev.devhandle = devhandle
    dev.usb_pid = usb_pid
    dev.flagsandattrs = flagsandattrs
    dev._cal_raw = {}
    dev._cal = {}
    dev._wavelength = None
    dev.load_calibration(0, "H15230", wavelength=633)

    # test version
    print(f"  Version: {dev.version(timeout=5)}")
    print(f"  Serial: {dev.serial_number(timeout=5)}")

    print(f"\n  Calibration table (port 0, {dev._wavelength:.0f} nm):")
    for mv, r in dev._cal[0]:
        print(f"    {mv:8.4f} mV  ->  {r:.4f} nm  ({r/dev._wavelength:.4f} waves)")

    print("\n  Retardance query (waves):")
    for port in (0, 1):
        try:
            r = dev.retardance(port, timeout=3)
            print(f"    Port {port}: {r:.4f} waves")
        except D5020Error as e:
            print(f"    Port {port}: ERROR - {e}")

    print("\n  Set port 0 to 0.5 waves...")
    dev.set_retardance_waves(0, 0.5, timeout=3)
    r = dev.retardance(0, timeout=3)
    print(f"    Read back: {r:.4f} waves")

    print("\n  Set port 0 to 300 nm...")
    dev.set_retardance_nm(0, 300, timeout=3)
    r = dev.retardance(0, timeout=3)
    print(f"    Read back: {r:.4f} waves  ({r * dev._wavelength:.1f} nm)")

    print("\n  Set port 0 to 0.0 waves...")
    dev.set_retardance_waves(0, 0.0, timeout=3)

    mlousb.USBDRVD_CloseDevice(devhandle)
    print("\nDone")
