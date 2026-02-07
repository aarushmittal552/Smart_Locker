from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from db import get_db
import hardware
import os

app = Flask(__name__)
CORS(app)

# Serve static files from media folder
@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory('media', filename)


# ============ STATE ============
current_locker_pin = "1234"
enrollment_mode = False
last_scanned_uid = None
last_scanned_card_user = None
arduino_command_queue = []

# ============ AUTH ENDPOINTS ============
@app.route("/login", methods=["POST"])
def login():
    """Login endpoint for frontend"""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
        
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
    user = cur.fetchone()
    
    if user:
        return jsonify({
            "success": True, 
            "username": user["username"], 
            "role": user["role"]
        })
    else:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401


# ============ ARDUINO COMMAND QUEUE ============
@app.route("/arduino/poll_commands", methods=["GET"])
def poll_arduino_commands():
    """Endpoint for serial_listener to poll for new commands"""
    global arduino_command_queue
    if arduino_command_queue:
        cmd = arduino_command_queue.pop(0)
        return jsonify({"command": cmd})
    return jsonify({"command": None})

def queue_arduino_command(cmd):
    global arduino_command_queue
    arduino_command_queue.append(cmd)
    log_message(f"Queued Arduino Command: {cmd}")

# ============ ENROLLMENT ENDPOINTS ============
@app.route("/api/cards/enroll-mode", methods=["POST"])
def set_enrollment_mode():
    """Enable or disable card enrollment mode (Admin only)"""
    role = request.headers.get("X-ROLE")
    if role != "admin":
        return jsonify({"success": False, "error": "Admin access required"}), 403

    global enrollment_mode, last_scanned_uid
    data = request.get_json()
    enrollment_mode = data.get("enabled", False)
    last_scanned_uid = None # Reset
    
    status_msg = "Enabled" if enrollment_mode else "Disabled"
    log_message(f"Enrollment Mode {status_msg}")
    return jsonify({"success": True, "enrollment_mode": enrollment_mode})

@app.route("/api/cards/last-scanned", methods=["GET"])
def get_last_scanned():
    """Get the last scanned UID (for UI)"""
    global last_scanned_uid
    return jsonify({"uid": last_scanned_uid})

@app.route("/api/cards/add", methods=["POST"])
def add_card():
    """Register a new card"""
    data = request.get_json()
    uid = data.get("uid")
    username = data.get("username")
    role = request.headers.get("X-ROLE")

    if role != "admin":
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    if not uid or not username:
        return jsonify({"success": False, "error": "Missing UID or Username"}), 400
        
    db = get_db()
    cur = db.cursor()
    try:
        # Check if user exists
        cur.execute("SELECT username FROM users WHERE username = %s", (username,))
        if not cur.fetchone():
             # Create dummy user if not exists (simplify flow)
             cur.execute("INSERT INTO users (username, password, role) VALUES (%s, '1234', 'user')", (username,))
        
        # Insert Card
        cur.execute("INSERT INTO rfid_cards (uid, username) VALUES (%s, %s)", (uid, username))
        db.commit()
        log_message(f"Card {uid} registered to {username}")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/user/locker", methods=["GET"])
def get_user_locker():
    """Get the locker assigned to a user"""
    username = request.headers.get("X-USER")
    role = request.headers.get("X-ROLE")
    
    if not username:
        return jsonify({"success": False, "error": "Username required"}), 400
    
    # Admin can access all lockers
    if role == "admin":
        return jsonify({"success": True, "lockers": ["LOCKER_1", "LOCKER_2", "LOCKER_3"], "is_admin": True})
    
    # Regular user - get their assigned locker
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT DISTINCT locker_id FROM rfid_cards WHERE username = %s AND is_active = 1", (username,))
        rows = cur.fetchall()
        lockers = [row["locker_id"] for row in rows]
        
        return jsonify({"success": True, "lockers": lockers, "is_admin": False})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============ ARDUINO EVENT ENDPOINT ============
@app.route("/arduino/event", methods=["POST"])
def arduino_event():
    """Receive events from Arduino via serial listener"""
    global last_scanned_uid, current_locker_pin
    data = request.get_json()
    
    event_type = data.get("type", "unknown")
    
    # 1. RFID SCANNED
    if event_type == "rfid_scanned":
        uid = data.get("uid")
        log_message(f"RFID Scanned: {uid}")
        
        if enrollment_mode:
            last_scanned_uid = uid
            hardware.short_beep() 
            log_message(f"Enrollment: Card {uid} scanned")
            return jsonify({"success": True, "action": "enrolled_wait"})
        
        # Auth Logic
        global last_scanned_card_user
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM rfid_cards WHERE uid = %s AND is_active = 1", (uid,))
        card = cur.fetchone()
        
        if card:
             last_scanned_card_user = card['username']
             log_message(f"Valid Card: {uid} ({card['username']}) - Requesting PIN")
             queue_arduino_command("REQUEST_PIN")
        else:
             last_scanned_card_user = None
             log_message(f"Invalid Card: {uid} - Access Denied")
             queue_arduino_command("DENY")
             hardware.capture_intruder_photo(uid=uid, locker_id="LOCKER_1") # Trigger camera on wrong card

    # 2. PIN ENTERED
    elif event_type == "pin_entered":
        pin = data.get("pin")
        
        if pin == current_locker_pin:
            log_message("PIN Verified - Unlocking")
            queue_arduino_command("OPEN")
            # For hardware events, we might not know the exact lock_id, 
            # but usually it's the one that just requested auth.
            # For now, let's assume it updates the default or we need more context.
            # If we want to support multiple lockers via serial, we need lock_id in the event.
            hardware.locker_states["LOCKER_1"] = "UNLOCKED" 
        else:
            log_message(f"Wrong PIN entered: {pin}")
            queue_arduino_command("DENY")
            hardware.capture_intruder_photo(uid=last_scanned_uid, locker_id="LOCKER_1") # Trigger camera on wrong PIN
            
    # 3. STATUS CHANGE
    elif event_type == "status_change":
        status = data.get("status")
        l_id = data.get("lock_id", "LOCKER_1")
        if status in ["UNLOCKED", "LOCKED"]:
             hardware.locker_states[l_id] = status
             
    # 4. INTRUDER
    elif event_type == "intruder":
        msg = data.get("message")
        log_message(msg)
        hardware.capture_intruder_photo(locker_id=data.get("lock_id", "LOCKER_1"))

    return jsonify({"success": True})

# ============ PIN MANAGEMENT ENDPOINTS ============
@app.route("/pin", methods=["GET"])
def get_pin():
    """Get current PIN (admin only - verify role in frontend)"""
    return jsonify({"pin": current_locker_pin})

@app.route("/pin", methods=["POST"])
def set_pin():
    """Set new PIN from web app"""
    global current_locker_pin
    
    data = request.get_json()
    new_pin = data.get("pin", "")
    role = request.headers.get("X-ROLE")
    user = request.headers.get("X-USER")
    
    # Only admin can change PIN from web
    if role != "admin":
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    # Validate PIN (4 digits)
    if not new_pin or len(new_pin) != 4 or not new_pin.isdigit():
        return jsonify({"success": False, "error": "PIN must be 4 digits"}), 400
    
    current_locker_pin = new_pin
    
    # Log the change
    log_message(f"ADMIN {user} changed PIN via web app")
    
    # Note: To sync with Arduino, the serial_listener will need to send SETPIN command
    # This is handled by the frontend calling a separate endpoint or the listener polling
    
    return jsonify({
        "success": True,
        "message": "PIN changed successfully",
        "arduino_sync": "Send SETPIN command to Arduino to sync"
    })

@app.route("/api/unlock-with-pin", methods=["POST"])
def unlock_with_pin():
    """Unlock locker with PIN verification"""
    global current_locker_pin
    
    data = request.get_json()
    pin = data.get("pin", "")
    user = request.headers.get("X-USER")
    role = request.headers.get("X-ROLE")
    lock_id = request.headers.get("X-LOCK-ID", "LOCKER_1")
    
    if not pin or len(pin) != 4:
        return jsonify({"success": False, "error": "PIN must be 4 digits"}), 400
    
    # Verify PIN
    if pin == current_locker_pin:
        # PIN correct - unlock
        hardware.locker_states[lock_id] = "UNLOCKED"
        queue_arduino_command("OPEN")
        log_message(f"{role.upper()} {user} unlocked {lock_id} with PIN")
        return jsonify({"success": True, "message": "Unlocked successfully"})
    else:
        # Wrong PIN - trigger intruder alert
        log_message(f"Wrong PIN attempt by {user} on {lock_id}")
        hardware.capture_intruder_photo(uid=user, locker_id=lock_id)
        return jsonify({"success": False, "error": "Wrong PIN - Intruder alert triggered"}), 401

@app.route("/arduino/command", methods=["POST"])
def send_arduino_command():
    """Queue a command to be sent to Arduino"""
    data = request.get_json()
    command = data.get("command", "")
    
    # This would be picked up by serial_listener
    # For now, just log it
    log_message(f"Arduino command queued: {command}")
    
    return jsonify({"success": True, "command": command})

# ============ HARDWARE STATUS & TEST ============
@app.route("/hardware/status")
def hardware_status():
    """Get current hardware connection status"""
    lock_id = request.args.get("lock_id", "LOCKER_1")
    return jsonify({
        "connected": hardware.arduino_connected,
        "status": hardware.locker_states.get(lock_id, "LOCKED"),
        "green_led": hardware.led_green_state,
        "red_led": hardware.led_red_state,
        "buzzer": hardware.buzzer_state
    })

@app.route("/hardware/test", methods=["POST"])
def hardware_test():
    """Trigger a hardware test - blinks LEDs and buzzer"""
    hardware.trigger_test()
    log_message("Hardware test triggered from web app")
    return jsonify({"success": True, "message": "Test sequence sent to Arduino"})

@app.route("/status", methods=["GET"])
def get_system_status():
    """Get overall system status"""
    lock_id = request.args.get("lock_id", "LOCKER_1")
    return jsonify({"status": hardware.locker_states.get(lock_id, "LOCKED")})

# ============ SIMULATION ENDPOINTS (NEW) ============
@app.route("/api/simulate/scan", methods=["POST"])
def simulate_scan():
    """Simulate an RFID scan event (for testing without hardware)"""
    data = request.get_json()
    uid = data.get("uid")
    
    if not uid:
        return jsonify({"success": False, "error": "UID required"}), 400
        
    # Inject into hardware logic
    result = hardware.simulate_scan(uid)
    
    # Also trigger the standard event logic so the backend processes it fully
    # This mocks what serial_listener would do
    with app.test_client() as client:
        client.post("/arduino/event", json={
            "type": "rfid_scanned",
            "uid": uid
        })
        
    return jsonify({"success": True, "result": result})

@app.route("/api/simulate/pin", methods=["POST"])
def simulate_pin():
    """Simulate a PIN entry event"""
    data = request.get_json()
    pin = data.get("pin")
    
    if not pin:
        return jsonify({"success": False, "error": "PIN required"}), 400
        
    hardware.simulate_pin(pin)
    
    # Trigger event logic
    with app.test_client() as client:
        client.post("/arduino/event", json={
            "type": "pin_entered",
            "pin": pin
        })
        
    return jsonify({"success": True})

# ============ COMMAND ENDPOINT ============
@app.route("/command/<cmd>", methods=["POST"])
def handle_command(cmd):
    """Handle lock/unlock/reset commands from dashboard"""
    role = request.headers.get("X-ROLE")
    user = request.headers.get("X-USER")
    lock_id = request.headers.get("X-LOCK-ID", "LOCKER_1")
    
    cmd = cmd.lower()
    
    if cmd not in ["lock", "unlock", "reset"]:
        return jsonify({"success": False, "error": "Invalid command"}), 400
    
    # Use hardware module to handle the command
    result = hardware.handle_command(cmd, role, user, lock_id)
    
    # Only queue Arduino command if action was authorized (not an intruder)
    if "INTRUDER" not in result:
        if cmd == "unlock":
            queue_arduino_command("OPEN")
        elif cmd == "lock":
            queue_arduino_command("DENY")  # This triggers lock state on Arduino
        elif cmd == "reset":
            queue_arduino_command("DENY")
            hardware.locker_states[lock_id] = "LOCKED"
    
    # Log the action
    log_message(result)
    
    return jsonify({"success": True, "result": result})

# ============ LOGS ENDPOINT ============
@app.route("/logs", methods=["GET"])
def get_logs():
    """Fetch recent system logs"""
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT id, message, log_type, time FROM logs ORDER BY time DESC LIMIT 50")
        logs = cur.fetchall()
        
        # Convert datetime to string for JSON serialization
        for log in logs:
            if log.get("time"):
                log["time"] = log["time"].isoformat()
        
        return jsonify(logs)
    except Exception as e:
        print(f"Logs fetch error: {e}")
        return jsonify([])

# ============ HELPER FUNCTIONS ============
def log_message(message):
    """Log a message to database"""
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT INTO logs (message) VALUES (%s)", (message,))
        db.commit()
    except Exception as e:
        print(f"Log error: {e}")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

