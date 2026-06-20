import ctypes
import threading
from ctypes import wintypes


_DLL_NAME = r"C:\Users\Arin\PycharmProjects\cameratest\usbdrvd.dll"
_USB_PID = 5020
_FLAGS = 0x40000000


class D5020Error(Exception):
    pass


class D5020:
    def __init__(self, dll_path=None):
        path = dll_path or _DLL_NAME
        try:
            self._dll = ctypes.WinDLL(path)
        except OSError as e:
            we = getattr(e, "winerror", None)
            raise D5020Error(
                f"Failed to load {path}: {e}\n"
                f"  type={type(e).__name__}  winerror={we}  args={e.args}\n"
                f"\n"
                f"  === Debugging steps ===\n"
                f"  1. Is usbdrvd.dll in the search path?\n"
                f"  2. List deps: `dumpbin /dependents usbdrvd.dll`\n"
                f"  3. Install VC++ redist: https://aka.ms/vs/17/release/vc_redist.x64.exe\n"
                f"  4. 32-bit DLL with 64-bit Python? Match the architecture."
            )
        except Exception as e:
            raise D5020Error(f"Failed to load {path}: [{type(e).__name__}] {e}")
        self._setup_argtypes()
        self._dev = None

    def _setup_argtypes(self):
        d = self._dll
        d.USBDRVD_GetDevCount.restype = wintypes.UINT
        d.USBDRVD_GetDevCount.argtypes = [wintypes.UINT]

        d.USBDRVD_OpenDevice.restype = wintypes.HANDLE
        d.USBDRVD_OpenDevice.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.UINT]

        d.USBDRVD_InterruptWrite.restype = wintypes.UINT
        d.USBDRVD_InterruptWrite.argtypes = [
            wintypes.HANDLE, wintypes.UINT,
            ctypes.POINTER(ctypes.c_byte), wintypes.UINT,
        ]

        d.USBDRVD_InterruptRead.restype = None
        d.USBDRVD_InterruptRead.argtypes = [
            wintypes.HANDLE, wintypes.UINT,
            ctypes.POINTER(ctypes.c_byte), wintypes.UINT,
        ]

        d.USBDRVD_CloseDevice.argtypes = [wintypes.HANDLE]

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

    def close(self):
        if self._dev:
            self._dll.USBDRVD_CloseDevice(self._dev)
            self._dev = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    def _make_cmd(cmdstr):
        cmdlen = len(cmdstr) + 1
        cmdarr = (ctypes.c_byte * cmdlen)()
        for i, ch in enumerate(cmdstr):
            cmdarr[i] = ord(ch)
        cmdarr[cmdlen - 1] = 13
        return cmdarr, cmdlen

    @staticmethod
    def _buffer_to_str(buf):
        parts = []
        for i in range(64):
            if buf[i] == 13:
                break
            parts.append(chr(buf[i]))
        return "".join(parts)

    def _cmd(self, command, timeout=None):
        if timeout is None:
            timeout = getattr(self, "_cmd_timeout", 3.0)
        if not self._dev:
            raise D5020Error("Device not opened")

        cmdarr, cmdlen = self._make_cmd(command)
        cmdptr = ctypes.cast(cmdarr, ctypes.POINTER(ctypes.c_byte))

        def do_write():
            return self._dll.USBDRVD_InterruptWrite(
                self._dev, 1, cmdptr, cmdlen
            )

        wret = [0]
        wexc = []
        def _write():
            try:
                wret[0] = do_write()
            except Exception as e:
                wexc.append(e)
        wt = threading.Thread(target=_write, daemon=True)
        wt.start()
        wt.join(timeout)
        if wt.is_alive():
            raise D5020Error(f"InterruptWrite timed out (cmd={command})")
        if wexc:
            raise D5020Error(f"InterruptWrite error: {wexc[0]}")

        buf = (ctypes.c_byte * 64)()
        rexc = []
        def _read():
            try:
                self._dll.USBDRVD_InterruptRead(self._dev, 0, buf, 64)
            except Exception as e:
                rexc.append(e)
        rt = threading.Thread(target=_read, daemon=True)
        rt.start()
        rt.join(timeout)
        if rt.is_alive():
            raise D5020Error(f"InterruptRead timed out (cmd={command})")
        if rexc:
            raise D5020Error(f"InterruptRead error: {rexc[0]}")

        return self._buffer_to_str(buf)

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
    import argparse

    parser = argparse.ArgumentParser(description="D5020 LCD controller test")
    parser.add_argument("--dll", default=r"C:\Users\Arin\PycharmProjects\cameratest\usbdrvd.dll")
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()

    dev = D5020(dll_path=args.dll)
    dev._cmd_timeout = args.timeout
    count = dev.device_count()
    print(f"Devices found: {count}")
    if count < 1:
        print("No D5020 devices present.")
        exit(1)

    with dev:
        dev.open(1)
        try:
            print(f"Version: {dev.version()}")
        except D5020Error as e:
            print(f"Error: {e}")
            print("Device found but not responding. Check command format.")
            exit(1)

        for port in (0, 1):
            try:
                v = dev.retardance(port)
                print(f"Port {port} retardance: {v}")
            except D5020Error as e:
                print(f"Port {port}: {e}")

        try:
            t = dev.temperature()
            print(f"Temperature: {t}")
        except D5020Error:
            print("Temperature not available")

        print("Setting port 0 to 0.500 ...")
        try:
            dev.retardance(0, 0.500)
            print(f"  Port 0 now: {dev.retardance(0)}")
        except D5020Error as e:
            print(f"  Set failed: {e}")
