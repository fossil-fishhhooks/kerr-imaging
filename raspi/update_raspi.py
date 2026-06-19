import serial
import serial.tools.list_ports
import time
import base64
import os
import sys


def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports if 'USB' in port.description or 'Serial' in port.description]


def send(ser, cmd, delay=0.05):
    ser.write(cmd.encode('utf-8'))
    time.sleep(delay)


def read_until(ser, timeout=3):
    output = b""
    ser.timeout = timeout
    while True:
        try:
            data = ser.read(1024)
            if not data:
                break
            output += data
        except:
            break
    return output.decode('utf-8', errors='replace')


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("Error: admin privileges required for serial port access. Run as Administrator.")
                sys.exit(1)
        except:
            print("Warning: could not verify admin privileges on Windows. Proceeding anyway...")
    elif os.geteuid() != 0:
        print("Error: root privileges required for serial port access. Run with sudo.")
        sys.exit(1)

    ports = list_serial_ports()
    if not ports:
        print("No serial ports found. Is the RPi connected?")
        sys.exit(1)

    if len(ports) == 1:
        port = ports[0]
        print(f"Found port: {port}")
    else:
        print("Available ports:")
        for i, p in enumerate(ports):
            print(f"  {i}: {p}")
        port = ports[int(input("Select port number: "))]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_c_path = os.path.join(script_dir, 'firmware', 'main.c')
    if not os.path.exists(main_c_path):
        print(f"Error: {main_c_path} not found")
        sys.exit(1)

    ser = serial.Serial(port, baudrate=9600, timeout=1)
    time.sleep(1.5)
    ser.reset_output_buffer()
    ser.reset_input_buffer()

    send(ser, "\r\r\r\r\r\r\r")
    time.sleep(1)
    output = read_until(ser, timeout=1)
    print(f"RPi says: {output.strip() or '(silent)'}")

    if "login:" in output.lower():
        print("Login prompt detected. Sending credentials...")
        send(ser, "arin\r", 0.5)
        send(ser, "pi\r", 2)
        output = read_until(ser, timeout=1)
        print(f"After login: {output.strip()}")

    send(ser, "\x03", 0.3)
    send(ser, "\r", 0.3)
    send(ser, "echo SHELL_OK\r", 0.5)
    output = read_until(ser, timeout=1)
    print(f"Shell check: {output.strip()}")

    if "SHELL_OK" not in output:
        print("WARNING: May not be at a shell prompt. Continuing anyway...")

    def transfer_file(local_path, remote_path, label):
        with open(local_path, 'rb') as f:
            data = f.read()
        encoded = base64.b64encode(data).decode('ascii')
        print(f"Transferring {label} ({len(data)} bytes)...")

        send(ser, "printf '' > /tmp/tf.b64\r", 0.2)
        CHUNK = 120
        chunks = [encoded[i:i+CHUNK] for i in range(0, len(encoded), CHUNK)]
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            send(ser, f'printf "%s" "{chunk}" >> /tmp/tf.b64\r', 0.02)
            if (i + 1) % 30 == 0:
                print(f"  {i+1}/{total} chunks")

        send(ser, f'base64 -d /tmp/tf.b64 > {remote_path}\r', 0.3)
        send(ser, "rm /tmp/tf.b64\r", 0.1)

    print("Ensuring target directory exists...")
    send(ser, "mkdir -p ~/programs/DLP/systems\r", 0.3)

    transfer_file(main_c_path, "~/programs/DLP/systems/main.c", "main.c")

    config_path = os.path.join(script_dir, 'firmware', 'config.txt')
    if os.path.exists(config_path):
        transfer_file(config_path, "~/programs/DLP/systems/config.txt", "config.txt")

    print("Compiling...")
    send(ser, "cd ~/programs/DLP/systems && g++ -O3 main.c -o main.o -march=native -lm 2>&1\r", 0.5)
    time.sleep(8)
    send(ser, "echo BUILD_DONE\r", 0.5)
    time.sleep(1)
    output = read_until(ser, timeout=5)
    print(f"Build output:\n{output}")

    ser.close()

    if "BUILD_DONE" in output and "error" not in output.lower():
        print("Update complete. main.o rebuilt successfully.")
    else:
        print("Build may have had issues. Check output above.")


if __name__ == "__main__":
    main()
