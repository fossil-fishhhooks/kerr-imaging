# Illumination: higher-level coordination of all things DLP. uses IPG to control the DLP

import os
import ctypes


from ctypes import *
import time
from illumination import IPG
import subprocess
import math

# Load the DLL.
DLL_PATH = r"C:\Users\Arin\PycharmProjects\cameratest\DLP4710EVM_CY.dll"
try:
    dll = ctypes.WinDLL(DLL_PATH)
except Exception as e:
    raise RuntimeError(f"Failed to load DLL at {DLL_PATH}: {e}")

class DLP(Structure):
    _fields_ = [
        ("handle", c_void_p),
        ("id", c_ushort),
        ("ch", c_ushort)
    ]


dll.OpenWithAutoconnect.argtypes = [ctypes.POINTER(DLP), c_char_p]
dll.OpenWithAutoconnect.restype = c_int

dll.Open.argtypes = [c_ubyte, POINTER(DLP)]
dll.Close.restype = c_int

dll.WriteExternalVideoSourceFormat.argtypes = [DLP, c_uint8]
dll.WriteExternalVideoSourceFormat.restype = c_int

dll.WriteOperateMode.argtypes = [DLP, c_uint8]
dll.WriteOperateMode.restype = c_int

dll.WriteDisplaySize.argtypes = [DLP, c_uint16, c_uint16]
dll.WriteDisplaySize.restype = c_int

dll.Close.argtypes = [DLP]
dll.Close.restype = c_int

dll.Version.argtypes = [POINTER(c_int), POINTER(c_int)]



class Ill():



    def __init__(self,fname_acx_file, IPGport = "0", displayw = 1920, displayh = 1080):
        self.disph = displayh
        self.dispw = displayw
        x = c_int()
        y = c_int()
        dll.Version(byref(x), byref(y))
        print(f"[DLP INIT] Loaded Arins janky dll version {x.value}.{y.value}")
        self.DLP = DLP()

        print("[DLP INIT] Opened serial port to DLP with code ", end="")
        print(dll.OpenWithAutoconnect(byref(self.DLP), ctypes.c_char_p(fname_acx_file.encode('utf-8'))))

        print("[DLP INIT] Set input to HDMI with code ", end="")
        print(dll.WriteOperateMode(self.DLP, c_uint8(0x00)))

        print("[DLP INIT] Set video format with code ", end="")
        print(dll.WriteExternalVideoSourceFormat(self.DLP, c_uint8(0x43)))

        print("[DLP INIT] Set pattern size (maximum) with code ", end="")
        print(dll.WriteDisplaySize(self.DLP, c_uint16(displayw) , c_uint16(displayh)))

        print("[DLP INIT] Setup complete")


        #IPG stuff
        print("[IPG INIT] Listing devices; Pick IPG, or enter 0 to go without")
        ports = IPG.list_serial_ports()
        if (not ports ) or IPGport != "0":
            if IPGport != "0":
                print("[IPG INIT] Port given")
                print(f"[IPG INIT] Trying port {IPGport}")
                self.IPGPORT = IPGport
                #IPG.login_and_activate(self.IPGPORT)
                IPG.dumb_login((self.IPGPORT))
            else:
                print("[IPG INIT] No USB serial devices found. Going without")
                self.IPGPORT = 0
        else:
            self.IPGPORT = IPG.choose_port(ports)
            if self.IPGPORT == "0":
                pass
            else:
                print(f"[IPG INIT] Trying port {self.IPGPORT}")
                #IPG.login_and_activate(self.IPGPORT)
                IPG.dumb_login(self.IPGPORT)
                #IPG.main(self.IPGPORT)

        print("[IPG INIT] Setup complete")



    def arc(self, inradius, outradius, startang, endang, color):
        if outradius <= inradius:
            print("[DLP UPDT] Invalid arc")
            return
        if endang <= startang:
            print("[DLP UPDT] Invalid arc")
            return
        if outradius > self.disph/2:
            print("[DLP UPDT] Invalid arc")
            return
        if outradius > self.dispw/2:
            print("[DLP UPDT] Invalid arc")
            return

        print("[DLP UPDT] Arc write")
        print(f'arc {inradius} {outradius} {startang} {endang} {color}')
        IPG.send_message(self.IPGPORT, f'arc {inradius} {outradius} {startang} {endang} {color}\r')
        #IPG.send_message(self.IPGPORT, 'arc 30 90 30 90 35090\r')

    def restart_ipg(self):
        IPG.send_message(self.IPGPORT, "sudo shutdown -r now\r")
        print("[IPG STOP] Rebooted IPG. The system will not function until it is restarted. This object will no longer communicate with it.")
        self.IPGPORT = "0"

    def test_dlp(self):
        print("[DLP TEST] Starting")
        subprocess.run(["DLP4710EVM_CY_TEST.exe", "-test"])
        print("\n[DLP TEST] Completed")

    def dlp_standby(self):
        print("[DLP WAIT] Set standby with code ", end="")
        print(dll.WriteOperateMode(self.DLP, c_uint8(0xFF)))
    def dlp_standby_off(self):
        print("[DLP WAIT] Set standby off with code ", end="")
        print(dll.WriteOperateMode(self.DLP, c_uint8(0x00)))

    def __del__(self):
        self.dlp_standby()
        c = dll.Close(self.DLP)
        print(f"[DLP STOP] DLP object destroyed (requested self-destruct cleaned up DLP with code {c})")
        print("[IPG STOP] Left Rpi system as is")

    def __exit__(self, exc_type, exc_value, traceback):
        self.__del__()


x = Ill(os.path.join(os.path.dirname(__file__), "dlp.acx"))
# Arc settings
IN_RADIUS = 350
OUT_RADIUS = 400

for c in range(200):

    x.arc(IN_RADIUS, OUT_RADIUS, 0, 360, 200*c)
    x.arc(1, 200, 0, 360, 200 * c)
    time.sleep(0.02)
time.sleep(20)






