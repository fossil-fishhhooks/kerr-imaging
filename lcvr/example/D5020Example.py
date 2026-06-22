#Meadowlark Optics D5020 Python Example
#************************************************************************
#
#                               Meadowlark Optics
#                               Copyright (2022)
#
# File name: D5020_Example.py
#
# Description: This file contains sample source code that will initialize
#              a USB connection to a Meadowlark Optics D5020, send a
#              ver:? command and read the status response.
#              Note that this file is for use only on a 64 bit PC.
#              The 64 bit version of usbdrvd.dll is expected to be in
#              the folder with the example file. Tested with Python 3.10.
#
#************************************************************************

#import section
import os
import sys
from ctypes import *
from ctypes.wintypes import *

#helper function definitions
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
    
#DLL Setup
usbdrvdpath = os.path.dirname(__file__) + r"\..\..\usbdrvd" #Find usbdrvd.dll at path of this example file.
mlousb = WinDLL(usbdrvdpath) #Load the DLL.
#Set up return and argument defines for DLL Functions
mlousb.USBDRVD_OpenDevice.restype = HANDLE
mlousb.USBDRVD_InterruptWrite.argtypes = [HANDLE, c_uint, POINTER(c_byte), c_uint]
mlousb.USBDRVD_InterruptRead.argtypes = [HANDLE, c_uint, POINTER(c_byte), c_uint]
mlousb.USBDRVD_CloseDevice.argtypes = [HANDLE]

#Device variables
usb_pid = c_uint(5020) #Device PID for D5020
numdevices = c_uint(0)
devhandle = HANDLE();
flagsandattrs = c_uint(1073741824)
devnumber = c_uint(1)
writepipe = c_uint(1)
readpipe = c_uint(0)
bytecount = c_uint(0);

#command variables
cmdstr = "" #string of command
cmdlen = c_uint(0); #command length variable
usbbuffer = c_byte * 64 #controller response buffer definition
cmdstatus = usbbuffer() #variable to hold controller response
bufferlen = c_uint(64) #buffer size variable, set to default size of butter
cmdresponsestr = "" #Blank command response string variable.

# Find devices.  This example only talks to the first device found.
numdevices = mlousb.USBDRVD_GetDevCount(usb_pid)
if(numdevices == 0):
    sys.exit("No Devices Found.")
devicesfound = "Found "+str(numdevices)+" device(s)."
print(" ") #Print blank line
print (devicesfound) #then number of devices found
print(" ") #Print blank line

#Open Device
devhandle = mlousb.USBDRVD_OpenDevice(devnumber,flagsandattrs,usb_pid)

#Prep command to send
cmdstr = "ver:?"
(cmdtosend,cmdlen) = makecmd(cmdstr)
cmdptr = (c_byte * len(cmdtosend))(*cmdtosend)

#send command
bytecount = mlousb.USBDRVD_InterruptWrite(devhandle,writepipe,cmdptr,cmdlen)

#Read controller's response to command
mlousb.USBDRVD_InterruptRead(devhandle,readpipe,cmdstatus,bufferlen)
cmdresponsestr = buffer2str(cmdstatus) #Convert to string
print(cmdresponsestr) #Print controller's response

#More commands can be added using the command prep, write and read blocks.
#Reads must be done after each write to clear the buffer.  If the return
#value is unneeded, conversion to string and print are unnecessary.


#Close device.  Device should be opened at the beginning
#of the program and closed at the end of the program.
#Closing and reopening in the same program can cause issues.
mlousb.USBDRVD_CloseDevice(devhandle)
print(" ") #Print blank line

