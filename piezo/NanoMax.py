import serial
import time


class MDT693BError(Exception):
    pass


class RangeError(MDT693BError):
    pass


class DeviceError(MDT693BError):
    pass


class NanoMax_MDT693B:
    def __init__(self, port, baudrate=115200, timeout=0.5):
        self._ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
        for _ in range(3):
            info = self.msg("id?")
            if info and any("MDT693B" in line for line in info):
                break
            time.sleep(0.1)
        else:
            raise DeviceError(f"Not an MDT693B: {info}")

    def close(self):
        if self._ser and self._ser.is_open:
            self._ser.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def msg(self, cmd):
        self._ser.reset_input_buffer()
        self._ser.write((cmd + "\n").encode())
        self._ser.flush()
        raw = b""
        self._ser.timeout = 0.005
        while True:
            b = self._ser.read(1)
            if not b:
                break
            raw += b
        self._ser.timeout = 0.5
        text = raw.decode("utf-8", errors="replace")
        lines = [l.strip() for l in text.split("\r") if l.strip()]
        lines = [l for l in lines if l != ">"]
        return lines

    def _strip_val(self, lines):
        for line in lines:
            s = line.strip("*[] ")
            if s:
                return s
        return ""

    def _get_float(self, lines):
        v = self._strip_val(lines)
        try:
            return float(v)
        except ValueError:
            return 0.0

    def _get_int(self, lines):
        v = self._strip_val(lines)
        try:
            return int(v)
        except ValueError:
            return 0

    def _get_bool(self, lines):
        return self._get_int(lines) != 0

    # --- Identification & Display ---

    def id(self):
        return self.msg("id?")

    def commands(self):
        return self.msg("?")

    def echo(self, enable=None):
        if enable is None:
            return self._get_bool(self.msg("echo?"))
        return self.msg(f"echo={1 if enable else 0}")

    def display_intensity(self, value=None):
        if value is None:
            return self._get_int(self.msg("intensity?"))
        if not 0 <= value <= 15:
            raise RangeError("Display intensity must be 0-15")
        return self.msg(f"intensity={value}")

    def restore_factory(self):
        return self.msg("restore")

    # --- Voltage Limits ---

    def vlimit(self):
        return self._get_int(self.msg("vlimit?"))

    # --- General settings ---

    def friendly_name(self, name=None):
        if name is None:
            return self._strip_val(self.msg("friendly?"))
        return self.msg(f"friendly={name}")

    def serial_number(self):
        return self._strip_val(self.msg("serial?"))

    def dacstep(self, step=None):
        if step is None:
            return self._get_int(self.msg("dacstep?"))
        if not 1 <= step <= 1000:
            raise RangeError("DAC step must be 1-1000")
        return self.msg(f"dacstep={step}")

    def rotary_mode(self, mode=None):
        if mode is None:
            return self._get_int(self.msg("rotarymode?"))
        if mode not in (0, 1, 2):
            raise RangeError("Rotary mode must be 0, 1, or 2")
        return self.msg(f"rotarymode={mode}")

    def push_disable(self, disable=None):
        if disable is None:
            return self._get_bool(self.msg("pushdisable?"))
        return self.msg(f"pushdisable={1 if disable else 0}")

    def compat_mode(self, enable=None):
        if enable is None:
            return self._get_bool(self.msg("cm?"))
        return self.msg(f"cm={1 if enable else 0}")

    def sysmax_voltage(self, voltage=None):
        if voltage is None:
            return self._get_float(self.msg("sysmax?"))
        return self.msg(f"sysmax={voltage}")

    # --- Master Scan ---

    def ms_enable(self, enable=None):
        if enable is None:
            return self._get_bool(self.msg("msenable?"))
        return self.msg(f"msenable={1 if enable else 0}")

    def ms_voltage(self, voltage=None):
        if voltage is None:
            return self._get_float(self.msg("msvoltage?"))
        return self.msg(f"msvoltage={voltage}")

    # --- Per-axis voltage ---

    def _axis_voltage(self, axis, voltage=None):
        cmd = f"{axis.lower()}voltage"
        if voltage is None:
            return self._get_float(self.msg(f"{cmd}?"))
        if not 0 <= voltage <= 150:
            raise RangeError(f"{axis} voltage must be 0-150")
        self.msg(f"{cmd}={voltage}")

    def xvoltage(self, voltage=None):
        return self._axis_voltage("X", voltage)

    def yvoltage(self, voltage=None):
        return self._axis_voltage("Y", voltage)

    def zvoltage(self, voltage=None):
        return self._axis_voltage("Z", voltage)

    def allvoltage(self, voltage=None):
        if voltage is None:
            return self._get_float(self.msg("allvoltage?"))
        if not 0 <= voltage <= 150:
            raise RangeError("Voltage must be 0-150")
        self.msg(f"allvoltage={voltage}")

    def set_voltages(self, x=None, y=None, z=None):
        if x is not None:
            self.xvoltage(x)
        if y is not None:
            self.yvoltage(y)
        if z is not None:
            self.zvoltage(z)

    # --- Per-axis limits ---

    def _axis_min(self, axis, voltage=None):
        cmd = f"{axis.lower()}min"
        if voltage is None:
            return self._get_float(self.msg(f"{cmd}?"))
        self.msg(f"{cmd}={voltage}")

    def _axis_max(self, axis, voltage=None):
        cmd = f"{axis.lower()}max"
        if voltage is None:
            return self._get_float(self.msg(f"{cmd}?"))
        self.msg(f"{cmd}={voltage}")

    def xmin(self, voltage=None):
        return self._axis_min("X", voltage)

    def xmax(self, voltage=None):
        return self._axis_max("X", voltage)

    def ymin(self, voltage=None):
        return self._axis_min("Y", voltage)

    def ymax(self, voltage=None):
        return self._axis_max("Y", voltage)

    def zmin(self, voltage=None):
        return self._axis_min("Z", voltage)

    def zmax(self, voltage=None):
        return self._axis_max("Z", voltage)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MDT693B piezo controller test")
    parser.add_argument("--port", default="/dev/ttyACM0", help="Serial port (default: /dev/ttyACM0)") #COM6
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    with NanoMax_MDT693B(args.port, baudrate=args.baud) as nm:
        info = nm.id()
        print(f"Model: {next((l for l in info if 'Model' in l), 'unknown')}")
        print(f"FW: {next((l for l in info if 'Firmware' in l), 'unknown')}")
        print(f"Serial: {nm.serial_number()}")
        print(f"Vlimit: {nm.vlimit()},  DAC step: {nm.dacstep()}")
        print(f"  X={nm.xvoltage():7.2f}  Y={nm.yvoltage():7.2f}  Z={nm.zvoltage():7.2f} V")

        print("\nZ -> 25 V ...", end=" ")
        nm.zvoltage(25)
        time.sleep(0.5)
        print(f"{nm.zvoltage():.2f} V")

        print("X=10 Y=20 Z=30 ...", end=" ")
        nm.set_voltages(x=10, y=20, z=30)
        time.sleep(0.5)
        print(f"X={nm.xvoltage():.2f}  Y={nm.yvoltage():.2f}  Z={nm.zvoltage():.2f} V")

        print("All -> 0 V ...", end=" ")
        nm.allvoltage(0)
        time.sleep(0.5)
        print(f"X={nm.xvoltage():.2f}  Y={nm.yvoltage():.2f}  Z={nm.zvoltage():.2f} V")