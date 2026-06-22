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
    _dll.WriteCommand.argtypes = [DLPDevice, ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    _dll.WriteCommand.restype = ctypes.c_int
    _dll.WriteReadCommand.argtypes = [DLPDevice, ctypes.c_char_p, ctypes.c_int,
                                      ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_char_p]
    _dll.WriteReadCommand.restype = ctypes.c_int
    _dll.ReadOperateMode.argtypes = [DLPDevice, ctypes.POINTER(ctypes.c_uint8)]
    _dll.ReadOperateMode.restype = ctypes.c_int
    _dll.WriteTriggerOut.argtypes = [DLPDevice, ctypes.c_bool, ctypes.c_bool,
                                      ctypes.c_bool, ctypes.c_bool, ctypes.c_uint32]
    _dll.WriteTriggerOut.restype = ctypes.c_int
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


def dlp_write_command(dev, data, log=print):
    """Write raw bytes over I2C to the DLPC3479 (address 0x1B)."""
    if dev is None or not DLP_AVAILABLE:
        return -1
    _dll.SetI2CBusAccess(dev, True)
    tc = ctypes.c_int(0)
    ret = _dll.WriteCommand(dev, data, len(data), ctypes.byref(tc))
    _dll.SetI2CBusAccess(dev, False)
    log(f"WriteCommand({data.hex()}) = {ret}, transferred={tc.value}")
    return ret


def dlp_write_read_command(dev, write_data, read_len, log=print):
    """Write then read from the DLPC3479 I2C bus."""
    if dev is None or not DLP_AVAILABLE:
        return -1
    _dll.SetI2CBusAccess(dev, True)
    tc = ctypes.c_int(0)
    read_buf = ctypes.create_string_buffer(read_len)
    ret = _dll.WriteReadCommand(dev, write_data, len(write_data),
                                ctypes.byref(tc), read_len, read_buf)
    _dll.SetI2CBusAccess(dev, False)
    log(f"WriteReadCommand({write_data.hex()}) = {ret}, read={read_buf.raw[:read_len].hex()}")
    return ret, read_buf.raw[:read_len]


def dlp_read_operate_mode(dev, log=print):
    """Read the current operating mode of the DLP."""
    if dev is None or not DLP_AVAILABLE:
        return -1
    mode = ctypes.c_uint8(0)
    ret = _dll.ReadOperateMode(dev, ctypes.byref(mode))
    log(f"ReadOperateMode = {ret}, mode=0x{mode.value:02X}")
    return ret, mode.value


def dlp_write_reg(dev, reg, val, log=print):
    """Write a single DLPC3479 register: reg (1 byte) = val (1 byte)."""
    return dlp_write_command(dev, bytes([reg, val]), log=log)


def dlp_read_reg(dev, reg, log=print):
    """Read a single DLPC3479 register (write reg address, read 1 byte back)."""
    return dlp_write_read_command(dev, bytes([reg]), 1, log=log)


def dlp_write_input_image_size(dev, width, height, log=print):
    """Write Input Image Size (2Eh) — tell DLPC3479 incoming frame dimensions.

    Bytes 1-2: pixels per line (LSB, MSB), Bytes 3-4: lines per frame (LSB, MSB).
    """
    if dev is None or not DLP_AVAILABLE:
        return -1
    data = bytes([0x2E, width & 0xFF, (width >> 8) & 0xFF,
                  height & 0xFF, (height >> 8) & 0xFF])
    return dlp_write_command(dev, data, log=log)


def dlp_write_pattern_config(dev, seq_type=0x03, num_patterns=1,
                              illum_sel=0x07, log=print):
    """Write Pattern Configuration (96h).

    seq_type: 0x00=1bit mono, 0x01=1bit RGB, 0x02=8bit mono, 0x03=8bit RGB
    num_patterns: number of patterns in sequence (1 for single-pattern)
    illum_sel: bitmask b0=R, b1=G, b2=B (e.g. 0x02 = green only, 0x07 = all)
    """
    if dev is None or not DLP_AVAILABLE:
        return -1
    data = bytes([0x96, seq_type, num_patterns, illum_sel])
    return dlp_write_command(dev, data, log=log)


def dlp_read_pattern_config(dev, log=print):
    """Read Pattern Configuration (97h) — returns the current pattern config bytes."""
    if dev is None or not DLP_AVAILABLE:
        return -1, b''
    ret, data = dlp_write_read_command(dev, bytes([0x97]), 9, log=log)
    return ret, data


def dlp_write_trigger_out_config(dev, select=0, enable=True, polarity=False,
                                  invert=False, delay=0, log=print):
    """Configure Trigger Out signal via the DLL's WriteTriggerOut.

    select: 0=TRIG_OUT_1, 1=TRIG_OUT_2
    enable: True to enable trigger output
    polarity: output polarity
    invert: invert signal
    delay: delay in microseconds
    """
    if dev is None or not DLP_AVAILABLE:
        return -1
    ret = _dll.WriteTriggerOut(dev, ctypes.c_bool(select), ctypes.c_bool(enable),
                                ctypes.c_bool(polarity), ctypes.c_bool(invert),
                                ctypes.c_uint32(delay))
    log(f"WriteTriggerOut(sel={select}, en={enable}, pol={polarity}, "
        f"inv={invert}, delay={delay}) = {ret}")
    return ret


DLP_MODE_EXTERNAL_VIDEO = 0x00
DLP_MODE_EXTERNAL_PATTERN_STREAMING = 0x04
DLP_MODE_INTERNAL_PATTERN_STREAMING = 0x05
DLP_MODE_STANDBY = 0xFF


def dlp_set_operate_mode(dev, mode, log=print):
    """Set DLP operating mode via the DLL's WriteOperateMode."""
    if dev is None or not DLP_AVAILABLE:
        return -1
    ret = _dll.WriteOperateMode(dev, ctypes.c_uint8(mode))
    log(f"WriteOperateMode(0x{mode:02X}) = {ret}")
    return ret


def dlp_enable_external_pattern_streaming(dev, log=print):
    """Switch to External Pattern Streaming mode (0x04).

    The DLPC3479 captures each incoming HDMI frame as a pattern, bypassing
    the DMD's sequential R→G→B color subframe processing. LED illumination
    is set to white (all LEDs) — color is controlled via WriteRGBCurrentMax.

    Command sequence:
      1. Write Input Image Size (2Eh) — tell controller the frame dimensions
      2. Write Pattern Configuration (96h) — 8-bit RGB, 1 pat, all LEDs
      3. Configure Trigger Out 1 for camera sync
      4. Switches operating mode to 0x04
    """
    if dev is None or not DLP_AVAILABLE:
        return -1
    log("--- Enabling External Pattern Streaming mode ---")
    dlp_write_input_image_size(dev, 1920, 1080, log=log)
    dlp_write_pattern_config(dev, seq_type=0x03, num_patterns=1,
                              illum_sel=0x07, log=log)
    dlp_write_trigger_out_config(dev, select=0, enable=True,
                                  polarity=False, invert=False,
                                  delay=0, log=log)
    ret = dlp_set_operate_mode(dev, DLP_MODE_EXTERNAL_PATTERN_STREAMING, log=log)
    log(f"External Pattern Streaming enabled (ret={ret})")
    return ret


def dlp_disable_external_pattern_streaming(dev, log=print):
    """Revert to External Video Port mode (0x00)."""
    if dev is None or not DLP_AVAILABLE:
        return -1
    log("--- Disabling External Pattern Streaming ---")
    _dll.WriteTriggerOut(dev, ctypes.c_bool(0), ctypes.c_bool(False),
                          ctypes.c_bool(False), ctypes.c_bool(False),
                          ctypes.c_uint32(0))
    ret = dlp_set_operate_mode(dev, DLP_MODE_EXTERNAL_VIDEO, log=log)
    log(f"Back to External Video mode (ret={ret})")
    return ret


COLOR_MAP = {"Red": 16711680, "Green": 65280, "Blue": 255}
COLOR_RGB = {"Red": (255, 0, 0), "Green": (0, 255, 0), "Blue": (0, 0, 255)}
