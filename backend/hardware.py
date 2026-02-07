# Hardware simulation module for smart locker system
# This module simulates hardware interactions when physical hardware is not available

import os
from datetime import datetime

# Global state
arduino_connected = False
locker_states = {
    "LOCKER_1": "LOCKED",
    "LOCKER_2": "LOCKED", 
    "LOCKER_3": "LOCKED"
}
led_green_state = False
led_red_state = False
buzzer_state = False

def short_beep():
    """Simulate a short beep sound"""
    global buzzer_state
    buzzer_state = True
    print("[HARDWARE] Short beep")
    buzzer_state = False

def long_beep():
    """Simulate a long beep sound"""
    global buzzer_state
    buzzer_state = True
    print("[HARDWARE] Long beep")
    buzzer_state = False

def set_led(color, state):
    """Set LED state"""
    global led_green_state, led_red_state
    if color == "green":
        led_green_state = state
    elif color == "red":
        led_red_state = state
    print(f"[HARDWARE] LED {color} = {'ON' if state else 'OFF'}")

def trigger_test():
    """Trigger a hardware test sequence"""
    print("[HARDWARE] Running test sequence...")
    set_led("green", True)
    set_led("red", True)
    short_beep()
    set_led("green", False)
    set_led("red", False)
    print("[HARDWARE] Test complete")

def capture_intruder_photo(uid=None, locker_id="LOCKER_1"):
    """Capture intruder photo (simulated)"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"intruder_{locker_id}_{timestamp}.jpg"
    
    # Create media directory if it doesn't exist
    media_dir = os.path.join(os.path.dirname(__file__), "media")
    os.makedirs(media_dir, exist_ok=True)
    
    print(f"[HARDWARE] Capturing intruder photo: {filename}")
    print(f"[HARDWARE] UID: {uid}, Locker: {locker_id}")
    
    # In real implementation, this would capture from camera
    # For simulation, we just log it
    return filename

def simulate_scan(uid):
    """Simulate an RFID scan"""
    print(f"[HARDWARE] Simulated RFID scan: {uid}")
    short_beep()
    return {"scanned": True, "uid": uid}

def simulate_pin(pin):
    """Simulate PIN entry"""
    print(f"[HARDWARE] Simulated PIN entry: {'*' * len(pin)}")
    return {"entered": True}

def handle_command(cmd, role, user, lock_id):
    """Handle lock/unlock/reset commands"""
    global locker_states
    
    cmd = cmd.lower()
    
    if cmd == "unlock":
        if role == "admin":
            locker_states[lock_id] = "UNLOCKED"
            set_led("green", True)
            set_led("red", False)
            short_beep()
            return f"ADMIN {user} unlocked {lock_id}"
        else:
            # Non-admin trying to unlock - check permissions
            locker_states[lock_id] = "UNLOCKED"
            set_led("green", True)
            return f"USER {user} unlocked {lock_id}"
            
    elif cmd == "lock":
        locker_states[lock_id] = "LOCKED"
        set_led("green", False)
        set_led("red", True)
        short_beep()
        return f"{role.upper()} {user} locked {lock_id}"
        
    elif cmd == "reset":
        locker_states[lock_id] = "LOCKED"
        set_led("green", False)
        set_led("red", False)
        long_beep()
        return f"{role.upper()} {user} reset {lock_id}"
        
    return f"Unknown command: {cmd}"

def connect_arduino(port=None):
    """Attempt to connect to Arduino"""
    global arduino_connected
    print(f"[HARDWARE] Attempting Arduino connection on {port or 'auto-detect'}...")
    # Simulated - would use pyserial in real implementation
    arduino_connected = False
    print("[HARDWARE] Arduino not connected (simulation mode)")
    return arduino_connected

def disconnect_arduino():
    """Disconnect from Arduino"""
    global arduino_connected
    arduino_connected = False
    print("[HARDWARE] Arduino disconnected")
