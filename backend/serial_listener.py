"""
Serial Listener for Arduino Communication
Reads from Arduino USB serial and forwards events to Flask backend
"""

import serial
import serial.tools.list_ports
import requests
import time
import threading

BACKEND_URL = "http://127.0.0.1:5000"
BAUD_RATE = 9600

# Global serial connection
arduino = None
running = True

def find_arduino_port():
    """Find Arduino COM port automatically"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Common Arduino identifiers
        if "Arduino" in port.description or "CH340" in port.description or "USB" in port.description:
            return port.device
    return None

def connect_arduino():
    """Connect to Arduino serial port"""
    global arduino
    
    port = find_arduino_port()
    if port is None:
        print("Arduino not found. Available ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  - {p.device}: {p.description}")
        return False
    
    try:
        arduino = serial.Serial(port, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for Arduino reset
        print(f"Connected to Arduino on {port}")
        return True
    except Exception as e:
        print(f"Failed to connect to Arduino: {e}")
        return False

def send_to_backend(endpoint, data=None, method="POST"):
    """Send data to Flask backend"""
    try:
        url = f"{BACKEND_URL}{endpoint}"
        if method == "POST":
            res = requests.post(url, json=data, timeout=5)
        else:
            res = requests.get(url, timeout=5)
        return res.json()
    except Exception as e:
        print(f"Backend error: {e}")
        return None

def handle_arduino_message(message):
    """Process messages from Arduino"""
    message = message.strip()
    
    if not message:
        return
    
    print(f"Arduino: {message}")
    
    # Message format: TYPE:DATA
    parts = message.split(":", 1)
    msg_type = parts[0]
    msg_data = parts[1] if len(parts) > 1 else ""
    
    if msg_type == "RFID_SCANNED":
        send_to_backend("/arduino/event", {"type": "rfid_scanned", "uid": msg_data})
        
    elif msg_type == "PIN_ENTERED":
        send_to_backend("/arduino/event", {"type": "pin_entered", "pin": msg_data})
        
    elif msg_type == "STATUS":
        # STATUS:UNLOCKED, STATUS:DENIED, etc.
        send_to_backend("/arduino/event", {"type": "status_change", "status": msg_data})

    elif msg_type == "INTRUDER_DETECTED":
        send_to_backend("/arduino/event", {"type": "intruder", "message": f"Intruder Detected: {msg_data}"})
    
    elif msg_type == "SYSTEM_READY":
        print("Arduino system ready")


def send_command_to_arduino(command):
    """Send command to Arduino"""
    global arduino
    if arduino and arduino.is_open:
        arduino.write((command + "\n").encode())
        print(f"Sent to Arduino: {command}")
        return True
    return False

def listen_loop():
    """Main loop to listen for Arduino messages"""
    global arduino, running
    
    while running:
        if arduino and arduino.is_open:
            try:
                # 1. Read from Arduino
                if arduino.in_waiting > 0:
                    line = arduino.readline().decode('utf-8', errors='ignore')
                    handle_arduino_message(line)
                
                # 2. Check for commands from Backend (Poll)
                # Note: valid commands: OPEN, DENY, REQUEST_PIN
                try:
                    res = send_to_backend("/arduino/poll_commands", method="GET")
                    if res and res.get("command"):
                        send_command_to_arduino(res["command"])
                except:
                    pass
                    
            except Exception as e:
                print(f"Loop error: {e}")
                time.sleep(1)
        else:
            # Try to reconnect
            time.sleep(5)
            connect_arduino()
        
        # Don't hog CPU
        time.sleep(0.1)

def command_input_loop():
    """Loop to accept commands from user"""
    global running
    
    print("\nCommands: LOCK, UNLOCK, SETPIN:xxxx, STATUS, QUIT")
    
    while running:
        try:
            cmd = input("> ").strip().upper()
            if cmd == "QUIT":
                running = False
                break
            elif cmd:
                send_command_to_arduino(cmd)
        except EOFError:
            break
        except KeyboardInterrupt:
            running = False
            break

def main():
    global running
    
    print("=" * 50)
    print("Smart RFID Locker - Serial Listener")
    print("=" * 50)
    
    if not connect_arduino():
        print("\nRunning in demo mode (no Arduino connected)")
        print("Connect Arduino and restart to use hardware")
    
    # Start listening thread
    listen_thread = threading.Thread(target=listen_loop, daemon=True)
    listen_thread.start()
    
    # Run command input in main thread
    command_input_loop()
    
    # Cleanup
    if arduino and arduino.is_open:
        arduino.close()
    
    print("Serial listener stopped.")

if __name__ == "__main__":
    main()
