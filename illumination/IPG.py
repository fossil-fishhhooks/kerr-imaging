#IPG: python side of the raspi-based pattern generator
import serial
import serial.tools.list_ports
import time


def list_serial_ports():
    """List all available USB serial devices."""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports if 'USB' in port.description or 'Serial' in port.description]


def choose_port(ports):
    """Let the user choose a port from the list."""
    for i, port in enumerate(ports):
        print(f"{i + 1}. {port}")
    while True:
        try:
            choice = int(input("[IPG INIT] Select a port by number: ")) - 1
            if -1 == choice:
                return "0"
            if 0 <= choice < len(ports):
                return ports[choice]
            else:
                print("[IPG INIT] Invalid selection. Please choose a valid number.")
        except ValueError:
            print("[IPG INIT] Invalid input. Please enter a number.")


def send_message(port, message):
    """Send a message to the specified serial port."""
    try:
        with serial.Serial(port, baudrate=9600, timeout=1) as ser:
            ser.write(message.encode('utf-8'))

    except serial.SerialException as e:
        print(f"Error: {e}")


def main(chosen_port = "0"):
    if chosen_port == "0":
        ports = list_serial_ports()
        if not ports:
            print("No USB serial devices found.")
            return

        print("Available USB serial devices:")
        chosen_port = choose_port(ports)

        print(f"Selected port: {chosen_port}")

    data = serial.Serial(chosen_port, baudrate=9600, timeout=1).readline().decode('utf-8').strip()  # Read a line from the serial port
    print(data)
    if data:

        if "IPG login" in data:
            send_message(chosen_port, "arin\r")
            time.sleep(0.5)
            send_message(chosen_port, "pi\r")
            time.sleep(0.2)
            send_message(chosen_port, "/home/arin/programs/DLP/system/main.o\r")
            time.sleep(0.2)
            send_message(chosen_port, "\r")
        else:
            send_message(chosen_port, "*IDN?\r")
            data = serial.Serial(chosen_port, baudrate=9600, timeout=1).readline().decode('utf-8').strip()  # Read a line from the serial port
            if data:
                if "IPG" in data:
                    pass
                else:
                    send_message(chosen_port, "/home/arin/programs/DLP/system/main.o\r")
                    time.sleep(0.2)
                    send_message(chosen_port, "\r")

    send_message(chosen_port, "arc 30 100 10 99 75000\r")
   # while True:
   #     x = input("Enter arc command (arc r r theta theta color):")
   #     send_message(chosen_port, f"{x}\n")
   #     print(serial.Serial(chosen_port, baudrate=9600, timeout=1).readline().decode('utf-8').strip())  # Read a line from the serial port




def login_and_activate(chosen_port,go_again = True):
    data = serial.Serial(chosen_port, baudrate=9600, timeout=1).readline().decode(
        'utf-8').strip()  # Read a line from the serial port
    print(data)
    if data:

        if "IPG login" in data:
            print("[IPG INIT] Login required. Trying...")
            send_message(chosen_port, "arin\r")
            time.sleep(0.5)
            send_message(chosen_port, "pi\r")
            time.sleep(0.2)
            send_message(chosen_port, "/home/arin/programs/DLP/system/main.o\r")
            time.sleep(0.2)
            send_message(chosen_port, "\r")
        else:
            print("[IPG INIT] System already active")
            send_message(chosen_port, "\r\r\r\r\r\r\r\r*IDN?\r")
            time.sleep(1)
            data = serial.Serial(chosen_port, baudrate=9600, timeout=1).readline().decode(
                'utf-8').strip()  # Read a line from the serial port
            if data:
                if "IPG" in data:
                    print("[IPG INIT] Rpi core already running")
                else:
                    print("[IPG INIT] Starting Rpi core")
                    send_message(chosen_port, "/home/arin/programs/DLP/system/main.o\r")
                    time.sleep(0.2)
                    send_message(chosen_port, "\r")
    else:
        if go_again == True:
            send_message(chosen_port, "\r\r\r\r\r\r\r*IDN?\r")
            time.sleep(1)
            login_and_activate(chosen_port, go_again = False)
        else:
            print("[IPG INIT] Could not detect Rpi. This may occur if the system is preactivated")
            send_message(chosen_port, "\r\r\rarin\r")
            time.sleep(0.5)
            send_message(chosen_port, "pi\r")
            time.sleep(0.2)
            send_message(chosen_port, "/home/arin/programs/DLP/system/main.o\r")

def dumb_login(chosen_port):
    data = serial.Serial(chosen_port, baudrate=9600, timeout=1).readline().decode(
        'utf-8').strip()  # Read a line from the serial port
    print(data)
    time.sleep(0.5)
    send_message(chosen_port, "\r\r\r\r\r\r\rarin\r")
    data = serial.Serial(chosen_port, baudrate=9600, timeout=1).readline().decode(
        'utf-8').strip()  # Read a line from the serial port
    print(data)
    time.sleep(2.5)
    send_message(chosen_port, "pi\r")
    data = serial.Serial(chosen_port, baudrate=9600, timeout=1).readline().decode(
        'utf-8').strip()  # Read a line from the serial port
    print(data)
    time.sleep(0.2)
    send_message(chosen_port, "/home/arin/programs/DLP/system/main.o\r")
    time.sleep(3)
    data = serial.Serial(chosen_port, baudrate=9600, timeout=1).readline().decode(
        'utf-8').strip()  # Read a line from the serial port
    print(data)
    send_message(chosen_port, "\r\r\r\r\r\r\r")

if __name__ == "__main__":
    main()
