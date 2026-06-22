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


class D5020:
    def __init__(self, dll_path=None):
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
        if value is None:
            raw = self._cmd(f"port:{port}:retardance:?", timeout=timeout)
            return self._parse_float(raw)
        self._cmd(f"port:{port}:retardance:{value}", timeout=timeout)

    def temperature(self, timeout=None):
        raw = self._cmd("temp:?", timeout=timeout)
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
    # Same pattern as D5020Example.py — direct DLL calls, no class wrapper
    usbdrvdpath = r"C:\Users\Arin\PycharmProjects\cameratest\usbdrvd"
    mlousb = WinDLL(usbdrvdpath)
    mlousb.USBDRVD_OpenDevice.restype = HANDLE
    mlousb.USBDRVD_InterruptWrite.argtypes = [HANDLE, c_uint, POINTER(c_byte), c_uint]
    mlousb.USBDRVD_InterruptRead.argtypes = [HANDLE, c_uint, POINTER(c_byte), c_uint]
    mlousb.USBDRVD_CloseDevice.argtypes = [HANDLE]

    usb_pid = c_uint(5020)
    flagsandattrs = c_uint(1073741824)
    devnumber = c_uint(1)
    writepipe = c_uint(1)
    readpipe = c_uint(0)
    bufferlen = c_uint(64)

    n = mlousb.USBDRVD_GetDevCount(usb_pid)
    if n == 0:
        print("No Devices Found.")
        sys.exit(1)
    print(f"Found {n} device(s).\n")

    print("Opening device...")
    devhandle = mlousb.USBDRVD_OpenDevice(devnumber, flagsandattrs, usb_pid)
    print(f"devhandle = {devhandle}")
    print()

    # ver:?
    cmdstr = "ver:?"
    (cmdtosend, cmdlen) = makecmd(cmdstr)
    cmdptr = (c_byte * len(cmdtosend))(*cmdtosend)
    print(f"InterruptWrite ver:? (len={cmdlen})...")
    bc = mlousb.USBDRVD_InterruptWrite(devhandle, writepipe, cmdptr, cmdlen)
    print(f"  wrote {bc} bytes")
    usbbuffer = c_byte * 64
    cmdstatus = usbbuffer()
    print("InterruptRead for version...")
    mlousb.USBDRVD_InterruptRead(devhandle, readpipe, cmdstatus, bufferlen)
    print(f"  response: {buffer2str(cmdstatus)}")
    print()

    for port in (0, 1):
        cmdstr = f"port:{port}:retardance:?"
        (cmdtosend, cmdlen) = makecmd(cmdstr)
        cmdptr = (c_byte * len(cmdtosend))(*cmdtosend)
        print(f"InterruptWrite port:{port}:retardance:?...")
        bc = mlousb.USBDRVD_InterruptWrite(devhandle, writepipe, cmdptr, cmdlen)
        print(f"  wrote {bc} bytes")
        cmdstatus = usbbuffer()
        print(f"InterruptRead port {port}...")
        mlousb.USBDRVD_InterruptRead(devhandle, readpipe, cmdstatus, bufferlen)
        print(f"  response: {buffer2str(cmdstatus)}")

    print("\nClosing...")
    mlousb.USBDRVD_CloseDevice(devhandle)
    print("Done")
