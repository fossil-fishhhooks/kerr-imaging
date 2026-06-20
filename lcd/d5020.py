import os
from ctypes import *
from ctypes.wintypes import *

#helper function definitions
def makecmd (cmdstr):
    cmdlen = len(cmdstr) + 1
    cmdarr = c_byte * cmdlen
    cmdtosend = cmdarr()
    chartmp = 0
    for x in range(cmdlen - 1):
        chartmp = ord(cmdstr[x])
        cmdtosend[x] = chartmp
    cmdtosend[cmdlen-1] = 13
    return (cmdtosend,cmdlen)

def buffer2str (cmdstatus):
    responsestr = ""
    for x in range (64):
        if cmdstatus[x] == 13:
            break
        responsestr = responsestr + chr(cmdstatus[x])
    return responsestr


class D5020Error(Exception):
    pass


class D5020:
    def __init__(self, dll_path=None):
        if dll_path is None:
            dll_path = os.path.dirname(__file__) + r"\usbdrvd"
        try:
            self._dll = WinDLL(dll_path)
        except Exception as e:
            raise D5020Error(f"Failed to load {dll_path}: {e}")

        self._dll.USBDRVD_OpenDevice.restype = HANDLE
        self._dll.USBDRVD_InterruptWrite.argtypes = [HANDLE, c_uint, POINTER(c_byte), c_uint]
        self._dll.USBDRVD_InterruptRead.argtypes = [HANDLE, c_uint, POINTER(c_byte), c_uint]
        self._dll.USBDRVD_CloseDevice.argtypes = [HANDLE]

        self._dev = None
        self._usb_pid = c_uint(5020)
        self._flags = c_uint(1073741824)

    def device_count(self):
        return self._dll.USBDRVD_GetDevCount(self._usb_pid)

    def open(self, dev_number=1):
        if self._dev is not None:
            return
        num = self.device_count()
        if num == 0:
            raise D5020Error("No Devices Found.")
        self._dev = self._dll.USBDRVD_OpenDevice(dev_number, self._flags, self._usb_pid)
        if not self._dev:
            raise D5020Error("USBDRVD_OpenDevice returned NULL")

    def close(self):
        if self._dev:
            self._dll.USBDRVD_CloseDevice(self._dev)
            self._dev = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _cmd(self, command):
        if not self._dev:
            raise D5020Error("Device not opened")

        (cmdtosend, cmdlen) = makecmd(command)
        bytecount = self._dll.USBDRVD_InterruptWrite(
            self._dev, c_uint(1),
            (c_byte * len(cmdtosend))(*cmdtosend),
            cmdlen
        )

        usbbuffer = c_byte * 64
        cmdstatus = usbbuffer()
        self._dll.USBDRVD_InterruptRead(
            self._dev, c_uint(0), cmdstatus, c_uint(64)
        )
        return buffer2str(cmdstatus)

    def version(self):
        return self._cmd("ver:?")

    def retardance(self, port, value=None):
        if value is None:
            raw = self._cmd(f"port:{port}:retardance:?")
            return self._parse_float(raw)
        self._cmd(f"port:{port}:retardance:{value}")

    def temperature(self):
        raw = self._cmd("temp:?")
        return self._parse_float(raw)

    @staticmethod
    def _parse_float(raw):
        for tok in raw.replace(",", " ").split():
            try:
                return float(tok)
            except ValueError:
                continue
        return 0.0


if __name__ == "__main__":
    dllpath = os.path.dirname(__file__) + r"\..\example\usbdrvd"
    dev = D5020(dll_path=dllpath)

    numdevices = dev.device_count()
    if numdevices == 0:
        print("No Devices Found.")
        exit(1)

    print(" ")
    print(f"Found {numdevices} device(s).")
    print(" ")

    dev.open(1)

    v = dev.version()
    print(v)

    for port in (0, 1):
        try:
            r = dev.retardance(port)
            print(f"Port {port} retardance: {r}")
        except D5020Error as e:
            print(f"Port {port}: {e}")

    try:
        t = dev.temperature()
        print(f"Temperature: {t}")
    except D5020Error:
        print("Temperature not available")

    print(" ")
    print("Setting port 0 to 0.500 ...")
    try:
        dev.retardance(0, 0.500)
        print(f"  Port 0 now: {dev.retardance(0)}")
    except D5020Error as e:
        print(f"  Set failed: {e}")

    dev.close()
    print(" ")
