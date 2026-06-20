import ctypes
from ctypes import wintypes


_DLL_NAME = "usbdrvd.dll"
_USB_PID = 0x139C
_FLAGS = 0x40000000

_GUID_BYTES = bytes.fromhex("a22b5b8bc67041989385aaba9dfc7d2b")
_GUID_STRUCT = (ctypes.c_ubyte * 16).from_buffer_copy(_GUID_BYTES)


class D5020Error(Exception):
    pass


class D5020:
    def __init__(self, dll_path=None):
        path = dll_path or _DLL_NAME
        try:
            self._dll = ctypes.WinDLL(path)
        except Exception as e:
            raise D5020Error(f"Failed to load {path}: {e}")
        self._setup_argtypes()
        self._dev = None
        self._pipe0 = None
        self._pipe1 = None

    def _setup_argtypes(self):
        d = self._dll
        d.USBDRVD_GetDevCount.argtypes = [wintypes.DWORD]
        d.USBDRVD_GetDevCount.restype = wintypes.UINT

        d.USBDRVD_OpenDevice.argtypes = [wintypes.UINT, wintypes.DWORD, wintypes.DWORD]
        d.USBDRVD_OpenDevice.restype = wintypes.HANDLE

        d.USBDRVD_CloseDevice.argtypes = [wintypes.HANDLE]
        d.USBDRVD_CloseDevice.restype = None

        d.USBDRVD_PipeOpen.argtypes = [
            wintypes.UINT, wintypes.UINT, wintypes.DWORD,
            ctypes.POINTER(ctypes.c_ubyte * 16),
        ]
        d.USBDRVD_PipeOpen.restype = wintypes.HANDLE

        d.USBDRVD_PipeClose.argtypes = [wintypes.HANDLE]
        d.USBDRVD_PipeClose.restype = None

        d.USBDRVD_BulkWrite.argtypes = [
            wintypes.HANDLE, wintypes.ULONG,
            ctypes.c_char_p, wintypes.ULONG,
        ]
        d.USBDRVD_BulkWrite.restype = wintypes.ULONG

        d.USBDRVD_BulkRead.argtypes = [
            wintypes.HANDLE, wintypes.ULONG,
            ctypes.c_char_p, wintypes.ULONG,
        ]
        d.USBDRVD_BulkRead.restype = wintypes.ULONG

    def device_count(self):
        return self._dll.USBDRVD_GetDevCount(_USB_PID)

    def open(self, dev_num=1):
        if self._dev is not None:
            return
        count = self.device_count()
        if count < dev_num:
            raise D5020Error(f"Device {dev_num} not found (count={count})")
        self._dev = self._dll.USBDRVD_OpenDevice(dev_num, _FLAGS, _USB_PID)
        if not self._dev:
            raise D5020Error("USBDRVD_OpenDevice returned NULL")
        self._pipe0 = self._dll.USBDRVD_PipeOpen(dev_num, 0, _FLAGS, _GUID_STRUCT)
        self._pipe1 = self._dll.USBDRVD_PipeOpen(dev_num, 1, _FLAGS, _GUID_STRUCT)
        if not self._pipe0 or not self._pipe1:
            self.close()
            raise D5020Error("Failed to open pipes")

    def close(self):
        if self._pipe0:
            self._dll.USBDRVD_PipeClose(self._pipe0)
            self._pipe0 = None
        if self._pipe1:
            self._dll.USBDRVD_PipeClose(self._pipe1)
            self._pipe1 = None
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
        cmd_bytes = command.encode("ascii")
        written = self._dll.USBDRVD_BulkWrite(
            self._dev, 1, cmd_bytes, len(cmd_bytes)
        )
        if written != len(cmd_bytes):
            raise D5020Error(f"BulkWrite wrote {written} of {len(cmd_bytes)}")
        buf = ctypes.create_string_buffer(256)
        read = self._dll.USBDRVD_BulkRead(self._dev, 0, buf, 256)
        if read == 0:
            raise D5020Error("BulkRead returned 0 bytes")
        raw = buf.raw[:read]
        raw = raw.split(b"\r")[0].strip(b"\r\n\x00 ")
        return raw.decode("ascii", errors="replace")

    def version(self):
        return self._cmd("ver:?\n")

    def retardance(self, port, value=None):
        if value is None:
            raw = self._cmd(f"port:{port}:retardance:?\n")
            return self._parse_float(raw)
        self._cmd(f"port:{port}:retardance:{value}\n")

    def temperature(self):
        raw = self._cmd("temp:?\n")
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
    import argparse

    parser = argparse.ArgumentParser(description="D5020 LCD controller test")
    parser.add_argument("--dll", default="usbdrvd.dll", help="Path to usbdrvd.dll")
    args = parser.parse_args()

    dev = D5020(dll_path=args.dll)
    count = dev.device_count()
    print(f"Devices found: {count}")
    if count < 1:
        print("No D5020 devices present.")
        exit(1)

    with dev:
        dev.open(1)
        print(f"Version: {dev.version()}")
        for port in (0, 1):
            v = dev.retardance(port)
            print(f"Port {port} retardance: {v}")
        try:
            t = dev.temperature()
            print(f"Temperature: {t}")
        except Exception:
            print("Temperature not available")
        print("Setting port 0 to 0.500 ...")
        dev.retardance(0, 0.500)
        print(f"  Port 0 now: {dev.retardance(0)}")
        print("Setting port 0 back to 0.000 ...")
        dev.retardance(0, 0.000)
        print(f"  Port 0 now: {dev.retardance(0)}")
