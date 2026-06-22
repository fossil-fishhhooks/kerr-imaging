import ctypes
import os


DLP_AVAILABLE = False
_dll = None


class DLPDevice(ctypes.Structure):
    _fields_ = [
        ("handle", ctypes.c_void_p),
        ("id", ctypes.c_ushort),
        ("ch", ctypes.c_ushort),
    ]


_DLL_PATH = r"C:\Users\Arin\PycharmProjects\cameratest\DLP4710EVM_CY.dll"
try:
    _dll = ctypes.WinDLL(_DLL_PATH)
    _dll.OpenWithAutoconnect.argtypes = [ctypes.POINTER(DLPDevice), ctypes.c_char_p]
    _dll.OpenWithAutoconnect.restype = ctypes.c_int
    _dll.WriteOperateMode.argtypes = [DLPDevice, ctypes.c_uint8]
    _dll.WriteOperateMode.restype = ctypes.c_int
    _dll.WriteExternalVideoSourceFormat.argtypes = [DLPDevice, ctypes.c_uint8]
    _dll.WriteExternalVideoSourceFormat.restype = ctypes.c_int
    _dll.WriteDisplaySize.argtypes = [DLPDevice, ctypes.c_uint16, ctypes.c_uint16]
    _dll.WriteDisplaySize.restype = ctypes.c_int
    _dll.Close.argtypes = [DLPDevice]
    _dll.Close.restype = ctypes.c_int
    _dll.Version.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
    _dll.WriteRGBCurrent.argtypes = [DLPDevice, ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint16]
    _dll.WriteRGBCurrent.restype = ctypes.c_int
    _dll.WriteRGBCurrentMax.argtypes = [DLPDevice, ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint16]
    _dll.WriteRGBCurrentMax.restype = ctypes.c_int
    _dll.SetI2CBusAccess.argtypes = [DLPDevice, ctypes.c_bool]
    _dll.SetI2CBusAccess.restype = ctypes.c_int
    DLP_AVAILABLE = True
except Exception:
    pass


def dlp_open(acx_file=None):
    if not DLP_AVAILABLE:
        return None
    if acx_file is None:
        acx_file = os.path.join(os.path.dirname(__file__), "dlp.acx")
    dev = DLPDevice()
    ret = _dll.OpenWithAutoconnect(
        ctypes.byref(dev), ctypes.c_char_p(acx_file.encode())
    )
    if ret != 0:
        raise RuntimeError(f"DLP OpenWithAutoconnect returned {ret}")
    _dll.WriteOperateMode(dev, ctypes.c_uint8(0x00))
    _dll.WriteExternalVideoSourceFormat(dev, ctypes.c_uint8(0x43))
    _dll.WriteDisplaySize(dev, ctypes.c_uint16(1920), ctypes.c_uint16(1080))
    return dev


def dlp_close(dev):
    if dev is not None and DLP_AVAILABLE:
        _dll.WriteOperateMode(dev, ctypes.c_uint8(0xFF))
        ret = _dll.Close(dev)
        return ret
    return None


def _scale_rgb(r, g, b):
    """Scale 8-bit (0-255) RGB to 16-bit (0-65535) for the DLP API."""
    return (r * 257, g * 257, b * 257)


def dlp_set_rgb_current(dev, r, g, b, log=print):
    if dev is None or not DLP_AVAILABLE:
        return -1
    r16, g16, b16 = _scale_rgb(r, g, b)
    ret = _dll.WriteRGBCurrent(dev, ctypes.c_uint16(r16), ctypes.c_uint16(g16), ctypes.c_uint16(b16))
    log(f"WriteRGBCurrent({r16},{g16},{b16}) = {ret}")
    return ret


def dlp_set_rgb_current_max(dev, r, g, b, log=print):
    if dev is None or not DLP_AVAILABLE:
        return -1
    _dll.SetI2CBusAccess(dev, True)
    r16, g16, b16 = _scale_rgb(r, g, b)
    ret = _dll.WriteRGBCurrentMax(dev, ctypes.c_uint16(r16), ctypes.c_uint16(g16), ctypes.c_uint16(b16))
    ret2 = _dll.WriteRGBCurrent(dev, ctypes.c_uint16(r16), ctypes.c_uint16(g16), ctypes.c_uint16(b16))
    _dll.SetI2CBusAccess(dev, False)
    log(f"WriteRGBCurrentMax({r16},{g16},{b16}) = {ret}")
    log(f"WriteRGBCurrent({r16},{g16},{b16})   = {ret2}")
    return ret


COLOR_MAP = {"Red": 16711680, "Green": 65280, "Blue": 255}
COLOR_RGB = {"Red": (255, 0, 0), "Green": (0, 255, 0), "Blue": (0, 0, 255)}
