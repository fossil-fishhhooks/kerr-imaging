#Meadowlark Optics D5020 Python Wrapper

#************************************************************************

import os
import sys
import threading
from ctypes import *
from ctypes.wintypes import *

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


DEFAULT_CALIBRATION = [
    # (voltage_mV, retardance_waves) from Meadowlark LCVR datasheet (extracted)
    (0,     0.636),
    (967,   0.628),
    (1074,  0.616),
    (1128,  0.601),
    (1182,  0.587),
    (1235,  0.569),
    (1289,  0.555),
    (1343,  0.531),
    (1396,  0.514),
    (1450,  0.490),
    (1504,  0.479),
    (1558,  0.449),
    (1611,  0.423),
    (1665,  0.409),
    (1719,  0.391),
    (1772,  0.371),
    (1826,  0.347),
    (1880,  0.333),
    (1934,  0.321),
    (1987,  0.306),
    (2041,  0.292),
    (2095,  0.283),
    (2148,  0.271),
    (2202,  0.260),
    (2256,  0.248),
    (2363,  0.233),
    (2417,  0.225),
    (2524,  0.210),
    (2632,  0.198),
    (2685,  0.190),
    (2793,  0.181),
    (2900,  0.169),
    (3008,  0.160),
    (3115,  0.152),
    (3222,  0.143),
    (3384,  0.134),
    (3545,  0.125),
    (3921,  0.114),
    (4189,  0.105),
    (4511,  0.096),
    (4887,  0.087),
    (5424,  0.076),
    (6015,  0.067),
    (7197,  0.058),
    (8271,  0.049),
    (9613,  0.041),
    (12836, 0.032),
    (17669, 0.023),
    (20000, 0.000),
]


class D5020:
    def __init__(self, dll_path=None, calibration=None):
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
        self.set_calibration(calibration or DEFAULT_CALIBRATION)

    def set_calibration(self, table):
        """Set voltage(mV)->retardance(waves) calibration lookup table.

        *table* is a list of (voltage_mV, retardance_waves) pairs sorted by voltage.
        Retardance at 0V must be the maximum; voltage must be strictly increasing.
        """
        self._cal = sorted(table, key=lambda p: p[0])

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

    def _voltage_to_retardance(self, mv):
        return self._interp(self._cal, mv)

    def _retardance_to_voltage(self, waves):
        return self._rinterp(self._cal, max(0.0, waves))

    def device_count(self):
        return self.mlousb.USBDRVD_GetDevCount(self.usb_pid)

    def open(self, dev_number=1):
        if self.devhandle is not None:
            return
        if self.device_count() == 0:
            raise D5020Error("No Devices Found.")
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
        Uses the internal calibration table to convert between waves and millivolts.
        """
        channel = port + 1
        if value is None:
            raw = self._cmd(f"ld:{channel},?", timeout=timeout)
            mv = self._parse_float(raw)
            return self._voltage_to_retardance(mv)
        mv = self._retardance_to_voltage(value)
        self._cmd(f"ld:{channel},{mv}", timeout=timeout)

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
    dll = r"C:\Users\Arin\PycharmProjects\cameratest\usbdrvd"
    dev = D5020(dll_path=dll)
    n = dev.device_count()
    if n == 0:
        print("No Devices Found.")
        sys.exit(1)
    print(f"Found {n} device(s).\n")

    dev.open(1)
    print(f"  Version: {dev.version(timeout=5)}")
    print(f"  Serial: {dev.serial_number(timeout=5)}")

    print("\n  Calibration table:")
    for mv, r in dev._cal:
        print(f"    {mv:5d} mV  ->  {r:.3f} waves")

    print("\n  Retardance query:")
    for port in (0, 1):
        try:
            r = dev.retardance(port, timeout=3)
            print(f"    Port {port}: {r:.3f} waves")
        except D5020Error as e:
            print(f"    Port {port}: ERROR - {e}")

    print("\n  Set port 0 to 0.5 waves...")
    dev.retardance(0, 0.5, timeout=3)
    r = dev.retardance(0, timeout=3)
    print(f"    Read back: {r:.3f} waves")

    print("  Set port 0 to 0.0 waves...")
    dev.retardance(0, 0.0, timeout=3)

    dev.close()
    print("\nDone")
