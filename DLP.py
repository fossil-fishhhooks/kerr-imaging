import ctypes
from ctypes import *
import time


# -----------------------------------------------------------------------------
# Load the Cypress USB Serial DLL.
DLL_PATH = r"C:\Users\Arin\PycharmProjects\cameratest\cyusbserial.dll"
try:
    cyusbserial = ctypes.WinDLL(DLL_PATH)
except Exception as e:
    raise RuntimeError(f"Failed to load DLL at {DLL_PATH}: {e}")


def print_device_info(device_info):
    # Print the VID and PID:
    print("VID: 0x{:04X}".format(device_info.vidPid.vid))
    print("PID: 0x{:04X}".format(device_info.vidPid.pid))

    # Print the number of interfaces
    print("Number of Interfaces:", device_info.numInterfaces)

    # The string fields are stored as fixed-size arrays of UCHAR (c_ubyte).
    # We convert them to bytes, then split at the first null byte and decode.
    def array_to_str(arr):
        return bytes(arr).split(b'\x00')[0].decode('utf-8', errors='replace')

    manufacturer = array_to_str(device_info.manufacturerName)
    product = array_to_str(device_info.productName)
    serial = array_to_str(device_info.serialNum)
    friendly = array_to_str(device_info.deviceFriendlyName)

    print("Manufacturer Name:", manufacturer)
    print("Product Name:", product)
    print("Serial Number:", serial)
    print("Device Friendly Name:", friendly)

    # For deviceType and deviceClass, we print them as lists of integers.
    print("Device Types:", list(device_info.deviceType))
    print("Device Classes:", list(device_info.deviceClass))
    if "Vendor 1" in friendly:
        return True
    else:
        return False


# -----------------------------------------------------------------------------
# Define function prototypes based on the CSV export.

# CyGetListofDevices: gets the number of connected devices.
cyusbserial.CyGetListofDevices.argtypes = [ctypes.POINTER(c_int)]
cyusbserial.CyGetListofDevices.restype = c_int

# Define constants (adjust these as needed)
CY_STRING_DESCRIPTOR_SIZE = 256
CY_MAX_DEVICE_INTERFACE = 4

# Define UCHAR as an 8-bit unsigned integer
UCHAR = c_ubyte


# Define the CY_VID_PID structure (assuming it holds two unsigned shorts)
class CY_VID_PID(Structure):
    _fields_ = [
        ("vid", c_ushort),
        ("pid", c_ushort)
    ]


# Define CY_DEVICE_TYPE and CY_DEVICE_CLASS as arrays of UCHAR
CY_DEVICE_TYPE_ARRAY = UCHAR * CY_MAX_DEVICE_INTERFACE
CY_DEVICE_CLASS_ARRAY = UCHAR * CY_MAX_DEVICE_INTERFACE


# define a dummy CY_DEVICE_SERIAL_BLOCK
class CY_DEVICE_SERIAL_BLOCK(Structure):
    _fields_ = [
        ("dummy", c_int)  # Replace with the actual fields if known
    ]


# Now define the CY_DEVICE_INFO structure
class CY_DEVICE_INFO(Structure):
    _fields_ = [
        ("vidPid", CY_VID_PID),
        ("numInterfaces", UCHAR),
        ("manufacturerName", UCHAR * CY_STRING_DESCRIPTOR_SIZE),
        ("productName", UCHAR * CY_STRING_DESCRIPTOR_SIZE),
        ("serialNum", UCHAR * CY_STRING_DESCRIPTOR_SIZE),
        ("deviceFriendlyName", UCHAR * CY_STRING_DESCRIPTOR_SIZE),
        ("deviceType", CY_DEVICE_TYPE_ARRAY),
        ("deviceClass", CY_DEVICE_CLASS_ARRAY),
        ("deviceBlock", CY_DEVICE_SERIAL_BLOCK)  # Only valid on Windows
    ]


class CY_HANDLE(Structure):
    _fields_ = [
        ("handle", c_void_p)
    ]


class CY_I2C_CONFIG(Structure):
    _fields_ = [
        ("frequency", c_int32),
        ("slaveAddress", c_uint8),
        ("isMaster", c_bool),
        ("isClockStretch", c_bool)

    ]


class CY_I2C_DATA_CONFIG(Structure):
    _fields_ = [

        ("slaveAddress", c_uint8),
        ("isStopBit", c_bool),
        ("isNakBit", c_bool)

    ]


class CY_DATA_BUFFER(Structure):
    _fields_ = [

        ("buffer", POINTER(c_uint8)),
        ("length", c_int32),
        ("transferCount", c_int32)

    ]


# Now set up the function argument types. Here, the second argument
# is a pointer to CY_DEVICE_INFO.
# For example:
cyusbserial.CyGetDeviceInfo.argtypes = [c_int, POINTER(CY_DEVICE_INFO)]
cyusbserial.CyGetDeviceInfo.restype = c_int

# CyOpen: opens the device at the given index.
# Updated prototype: first parameter = device index (int), second = flags/channel (int).
# Returns a handle (c_void_p).
cyusbserial.CyOpen.argtypes = [c_int8, c_int8, POINTER(CY_HANDLE)]
cyusbserial.CyOpen.restype = c_int

# CyClose: closes the device.
cyusbserial.CyClose.argtypes = [CY_HANDLE]
cyusbserial.CyClose.restype = c_int

# CySetI2cConfig: configures the I²C interface.
cyusbserial.CySetI2cConfig.argtypes = [CY_HANDLE, POINTER(CY_I2C_CONFIG)]
cyusbserial.CySetI2cConfig.restype = c_int

cyusbserial.CyI2cWrite.argtypes = [CY_HANDLE, POINTER(CY_I2C_DATA_CONFIG), POINTER(CY_DATA_BUFFER), c_int32]
cyusbserial.CyI2cWrite.restype = c_int

cyusbserial.CySetGpioValue.argtypes = [CY_HANDLE, c_int8, c_int8]
cyusbserial.CySetGpioValue.restype = c_int

cyusbserial.CyGetGpioValue.argtypes = [CY_HANDLE, c_int8, POINTER(c_int8)]
cyusbserial.CyGetGpioValue.restype = c_int

cyusbserial.CyI2cRead.argtypes = [CY_HANDLE, POINTER(CY_I2C_DATA_CONFIG), POINTER(CY_DATA_BUFFER), c_int32]
cyusbserial.CyI2cRead.restype = c_int


def RequestI2cBusAccess(handle, tries = 1, yescode = 1):
    cyusbserial.CySetGpioValue(handle, 5, 1) #POINTER CHECK

    for _ in range(tries):

        time.sleep(0.5)
        cyusbserial.CySetGpioValue(handle, 9, 0) #POINTER CHECK
        cyusbserial.CySetGpioValue(handle, 5, 0)#POINTER CHECK

        print("Trying Hshake")
        x = c_int8()
        cyusbserial.CyGetGpioValue(handle, 6, byref(x))
        if x.value == yescode:
            break
        else:
            print(f"xval {x.value}")

    cyusbserial.CySetGpioValue(handle, 9, 1)


def RelinquishI2cBusAccess(handle):
    cyusbserial.CySetGpioValue(handle, 9, 0)#POINTER CHECK
    cyusbserial.CySetGpioValue(handle, 5, 0) #POINTER CHECK


def WriteI2cByte(handle, dataconfig, bytecode):
    RequestI2cBusAccess(handle)
    dat = c_uint8(bytecode)
    dat_ptr = cast(byref(dat), POINTER(c_ubyte))
    db = CY_DATA_BUFFER(dat_ptr, 1, 1)

    tc = cyusbserial.CyI2cWrite(handle, byref(dataconfig), byref(db), 500)
    RelinquishI2cBusAccess(handle)

    print(f"Write stat {tc}")
    return tc


def WriteI2cBytes(handle, dataconfig, bytecode, leng):
    RequestI2cBusAccess(handle)

    # Create an array of c_ubyte with the data
    data_array = (c_ubyte * len(bytecode))(*bytecode)
    print(data_array)

    db = CY_DATA_BUFFER(data_array, leng, 1)

    tc = cyusbserial.CyI2cWrite(handle, byref(dataconfig), byref(db), 500)
    RelinquishI2cBusAccess(handle)

    print(f"Write stat {tc}")
    return tc


def ReadI2cBytes(handle, leng):
    RequestI2cBusAccess(handle)

    buffer = CY_DATA_BUFFER()
    cyusbserial.CyI2cRead(handle, byref(data_config), byref(buffer), 500)
    RelinquishI2cBusAccess(handle)

    length = buffer.length
    if length <= 0:
        return b""
    # Create an array type of length 'length'
    array_type = c_uint8 * length
    # Cast the buffer pointer to a pointer to that array type, then get its contents
    data_array = cast(buffer.buffer, POINTER(array_type)).contents
    # Convert the array to a Python bytes object and return it
    return bytes(data_array)


# -----------------------------------------------------------------------------
def check_error(ret_code, func_name):
    if ret_code != 0:
        raise Exception(f"{func_name} failed with error code: {ret_code}")


# -----------------------------------------------------------------------------

data_config = CY_I2C_DATA_CONFIG(0x1b, False, False)


def analyze_ret_stat(ret):
    if ret == 0:
        return "CY_SUCCESS: API returned successfully without any errors."
    elif ret == 1:
        return "CY_ERROR_ACCESS_DENIED: Access of the API is denied for the application."
    elif ret == 2:
        return "CY_ERROR_DRIVER_INIT_FAILED: Driver initialisation failed."
    elif ret == 3:
        return "CY_ERROR_DEVICE_INFO_FETCH_FAILED: Device information fetch failed."
    elif ret == 4:
        return "CY_ERROR_DRIVER_OPEN_FAILED: Failed to open a device in the library."
    elif ret == 5:
        return "CY_ERROR_INVALID_PARAMETER: One or more parameters sent to the API was invalid."
    elif ret == 6:
        return "CY_ERROR_REQUEST_FAILED: Request sent to USB Serial device failed."
    elif ret == 7:
        return "CY_ERROR_DOWNLOAD_FAILED: Firmware download to the device failed."
    elif ret == 8:
        return "CY_ERROR_FIRMWARE_INVALID_SIGNATURE: Invalid Firmware signature in firmware file."
    elif ret == 9:
        return "CY_ERROR_INVALID_FIRMWARE: Invalid firmware."
    elif ret == 10:
        return "CY_ERROR_DEVICE_NOT_FOUND: Device disconnected."
    elif ret == 11:
        return "CY_ERROR_IO_TIMEOUT: Timed out while processing a user request."
    elif ret == 12:
        return "CY_ERROR_PIPE_HALTED: Pipe halted while trying to transfer data."
    elif ret == 13:
        return "CY_ERROR_BUFFER_OVERFLOW: Overflow of buffer while trying to read/write data."
    elif ret == 14:
        return "CY_ERROR_INVALID_HANDLE: Device handle is invalid."
    elif ret == 15:
        return "CY_ERROR_ALLOCATION_FAILED: Error in allocation of the resource inside the library."
    elif ret == 16:
        return "CY_ERROR_I2C_DEVICE_BUSY: I2C device busy."
    elif ret == 17:
        return "CY_ERROR_I2C_NAK_ERROR: I2C device NAK."
    elif ret == 18:
        return "CY_ERROR_I2C_ARBITRATION_ERROR: I2C bus arbitration error."
    elif ret == 19:
        return "CY_ERROR_I2C_BUS_ERROR: I2C bus error."
    elif ret == 20:
        return "CY_ERROR_I2C_BUS_BUSY: I2C bus is busy."
    elif ret == 21:
        return "CY_ERROR_I2C_STOP_BIT_SET: I2C master has sent a stop bit during a transaction."
    elif ret == 22:
        return "CY_ERROR_STATUS_MONITOR_EXIST: API failed because the SPI/UART status monitor thread already exists."
    else:
        return f"Unknown error code: {ret}"


def main():
    # 1. Get the number of connected Cypress devices.
    num_devices = c_int(0)
    ret = cyusbserial.CyGetListofDevices(byref(num_devices))
    check_error(ret, "CyGetListofDevices")
    print(f"Number of Cypress USB-Serial devices found: {num_devices.value}")

    if num_devices.value <= 0:
        print("No Cypress devices found. Exiting.")
        return

    device_info = CY_DEVICE_INFO()
    MFGdev = 0
    for j in range(num_devices.value):
        cyusbserial.CyGetDeviceInfo(j, byref(device_info))
        r = print_device_info(device_info)
        if r == True:
            MFGdev = j
        print("---------------------------------------------------------------------------")

    autopick = True  #autopick correct channel?

    dev_id = 0
    if autopick == False:
        print("Pick device ID:")
        dev_id = int(input())
    else:
        if MFGdev == 0:
            print("Not detected. Try setting the autopick variable to false and checking manually")
            quit()
        else:
            print("Channel detected (autopick success)")
            dev_id = MFGdev
    handle = CY_HANDLE()
    ret = cyusbserial.CyOpen(dev_id, 1, byref(handle))
    print(f'RETCODE: {ret}')
    if ret != 0:
        print("Oh no")
        quit()

    i2cconfig = CY_I2C_CONFIG(100000, 0x30, True, False)

    print(f"I2C configured with code {ret}")

    ret = WriteI2cBytes(handle, data_config, b'\x06', 1)
    analyze_ret_stat(ret)

    cx = ReadI2cBytes(handle, 4)
    print(cx)

    ret = cyusbserial.CyClose(handle)
    print(f"Handle closed with code {ret}")


if __name__ == "__main__":
    main()

