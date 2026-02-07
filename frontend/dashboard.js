const BACKEND = "http://127.0.0.1:5000";

const user = sessionStorage.getItem("user");
const role = sessionStorage.getItem("role");

// Initialize with LOCKER_1 or saved selection
let lockId = sessionStorage.getItem("lock_id") || "LOCKER_1";

// Reference to status display element
const statusEl = document.getElementById("system-status");

// Redirect to login if not authenticated
if (!user || !role) {
    window.location.href = "index.html";
}

// Set user info in header
document.getElementById("user").innerText = user;
document.getElementById("role").innerText = role.toUpperCase();

// Set role badge
const roleBadge = document.getElementById("role-badge");
roleBadge.innerText = role.toUpperCase();
roleBadge.classList.add(role === "admin" ? "role-admin" : "role-user");

// Show admin-only sections
if (role === "admin") {
    const mainContainer = document.getElementById("main-container");
    if (mainContainer) {
        mainContainer.classList.add("is-admin");
    } else {
        console.error("Main container not found - admin styles may be broken");
    }
}

// Handle Locker Selection
const lockerSelect = document.getElementById("locker-select");

// Fetch user's assigned lockers and restrict dropdown
async function initLockerAccess() {
    try {
        const res = await fetch(`${BACKEND}/api/user/locker`, {
            headers: {
                "X-USER": user,
                "X-ROLE": role
            }
        });
        const data = await res.json();

        if (data.success && lockerSelect) {
            if (data.is_admin) {
                // Admin can access all lockers
                lockerSelect.value = lockId;
            } else {
                // User - restrict to their assigned lockers only
                const userLockers = data.lockers;

                if (userLockers.length === 0) {
                    // No locker assigned
                    lockerSelect.innerHTML = '<option value="">No locker assigned</option>';
                    lockerSelect.disabled = true;
                    showToast("No locker assigned to your account", "error");
                } else {
                    // Filter dropdown to only show user's lockers
                    Array.from(lockerSelect.options).forEach(option => {
                        if (!userLockers.includes(option.value)) {
                            option.remove();
                        }
                    });

                    // Set to user's first locker
                    lockId = userLockers[0];
                    lockerSelect.value = lockId;
                    sessionStorage.setItem("lock_id", lockId);

                    // If only one locker, disable selection
                    if (userLockers.length === 1) {
                        lockerSelect.disabled = true;
                    }
                }
            }
        }
    } catch (e) {
        console.error("Failed to fetch user locker access:", e);
    }
}

// Call on page load
initLockerAccess();

if (lockerSelect) {
    lockerSelect.onchange = (e) => {
        lockId = e.target.value;
        sessionStorage.setItem("lock_id", lockId);
        showToast(`Switched to ${lockId}`, "info");
        refreshStatus(); // Refresh status for new locker
    };
}

// Simple toast notification (beginner style)
function showToast(message, type = "info") {
    // Remove old toast if exists
    const old = document.querySelector(".toast");
    if (old) old.remove();

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerText = message;
    document.body.appendChild(toast);

    // Remove after 3 seconds
    setTimeout(() => toast.remove(), 3000);
}

// Unlock with PIN
async function unlockWithPIN() {
    const pinInput = document.getElementById("unlock-pin");
    const msgEl = document.getElementById("pin-unlock-message");
    const pin = pinInput.value;

    if (!pin || pin.length !== 4 || !/^\d{4}$/.test(pin)) {
        msgEl.innerHTML = '<span style="color:#f87171;">PIN must be 4 digits</span>';
        return;
    }

    try {
        const res = await fetch(`${BACKEND}/api/unlock-with-pin`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-USER": user,
                "X-ROLE": role,
                "X-LOCK-ID": lockId
            },
            body: JSON.stringify({ pin: pin })
        });

        const data = await res.json();

        if (data.success) {
            msgEl.innerHTML = '<span style="color:#4ade80;">✓ Unlocked!</span>';
            pinInput.value = "";
            showToast("Locker unlocked!", "success");
            refreshStatus();
        } else {
            msgEl.innerHTML = `<span style="color:#f87171;">✗ ${data.error || "Wrong PIN"}</span>`;
            showToast("Wrong PIN!", "error");
        }

        setTimeout(() => { msgEl.innerHTML = ""; }, 3000);
    } catch (e) {
        msgEl.innerHTML = '<span style="color:#f87171;">Backend not reachable</span>';
        console.error("PIN unlock error:", e);
    }
}

// Only allow numbers in PIN inputs
document.getElementById("unlock-pin")?.addEventListener("input", function (e) {
    this.value = this.value.replace(/[^0-9]/g, "");
});

document.getElementById("new-reset-pin")?.addEventListener("input", function (e) {
    this.value = this.value.replace(/[^0-9]/g, "");
});

// Show/hide reset PIN form
function showResetPIN() {
    const form = document.getElementById("reset-pin-form");
    if (form) {
        form.style.display = form.style.display === "none" ? "block" : "none";
    }
}

// Reset PIN function
async function resetPIN() {
    const pinInput = document.getElementById("new-reset-pin");
    const msgEl = document.getElementById("reset-pin-message");
    const pin = pinInput.value;

    if (!pin || pin.length !== 4 || !/^\d{4}$/.test(pin)) {
        msgEl.innerHTML = '<span style="color:#f87171;">PIN must be 4 digits</span>';
        return;
    }

    try {
        const res = await fetch(`${BACKEND}/pin`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-USER": user,
                "X-ROLE": role
            },
            body: JSON.stringify({ pin: pin })
        });

        const data = await res.json();

        if (res.ok && data.success) {
            msgEl.innerHTML = '<span style="color:#4ade80;">✓ PIN updated!</span>';
            pinInput.value = "";
            showToast("PIN changed successfully!", "success");
            setTimeout(() => {
                msgEl.innerHTML = "";
                document.getElementById("reset-pin-form").style.display = "none";
            }, 2000);
        } else {
            msgEl.innerHTML = `<span style="color:#f87171;">✗ ${data.error || "Failed to update PIN"}</span>`;
        }
    } catch (e) {
        msgEl.innerHTML = '<span style="color:#f87171;">Backend not reachable</span>';
        console.error("Reset PIN error:", e);
    }
}

// Update status display with color coding and glow effects
function updateStatusDisplay(status) {
    statusEl.innerText = status;
    statusEl.classList.remove("status-locked", "status-unlocked", "glow-red", "glow-green");

    // Update lock icon
    const lockIcon = document.getElementById("lock-icon");

    // Update LED indicators
    const greenLed = document.getElementById("led-green");
    const redLed = document.getElementById("led-red");

    if (greenLed && redLed) {
        greenLed.classList.remove("on", "blink");
        redLed.classList.remove("on", "blink");

        if (status === "LOCKED") {
            statusEl.classList.add("status-locked", "glow-red");
            redLed.classList.add("on");
            if (lockIcon) {
                lockIcon.innerText = "🔒";
                lockIcon.style.filter = "";
            }
        } else if (status === "UNLOCKED") {
            statusEl.classList.add("status-unlocked", "glow-green");
            greenLed.classList.add("on");
            if (lockIcon) {
                lockIcon.innerText = "🔓";
                lockIcon.style.filter = "hue-rotate(85deg) saturate(1.5)";
            }
        }
    }
}

// Refresh system status from backend
async function refreshStatus() {
    try {
        const res = await fetch(`${BACKEND}/status?lock_id=${lockId}`);
        if (!res.ok) throw new Error("Backend error");
        const data = await res.json();
        updateStatusDisplay(data.status);
    } catch (e) {
        statusEl.innerText = "Backend not reachable";
        statusEl.style.color = "#f59e0b";
        console.error("Status fetch error:", e);
    }
}

// Send command to backend
async function sendCommand(cmd) {
    try {
        const res = await fetch(`${BACKEND}/command/${cmd}`, {
            method: "POST",
            headers: {
                "X-ROLE": role,
                "X-USER": user,
                "X-LOCK-ID": lockId
            }
        });

        if (!res.ok) throw new Error("Command failed");

        const data = await res.json();
        console.log("Command result:", data.result);

        // Show success toast
        showToast(`${cmd.toUpperCase()} command sent!`, "success");

        // Refresh status after command
        refreshStatus();
    } catch (e) {
        showToast("Backend not reachable!", "error");
        console.error("Command error:", e);
    }
}

// Attach event listeners to buttons
document.getElementById("lock-btn").onclick = () => sendCommand("lock");
document.getElementById("unlock-btn").onclick = () => sendCommand("unlock");
document.getElementById("reset-btn").onclick = () => sendCommand("reset");

// ============ CARD ENROLLMENT ============
let enrollmentActive = false;
let enrollmentPollInterval = null;

async function toggleEnrollment() {
    enrollmentActive = !enrollmentActive;

    // UI Update
    const btn = document.getElementById("enroll-btn");
    const status = document.getElementById("enroll-status");

    if (enrollmentActive) {
        btn.innerText = "Stop Enrollment";
        btn.style.background = "linear-gradient(135deg, #ef4444, #dc2626)"; // Red to stop
        status.innerText = "Status: 📡 Scanning for new cards...";
        status.style.color = "#60a5fa";
        status.classList.add("blink");

        // Start Polling
        startEnrollmentPolling();
    } else {
        btn.innerText = "Start Enrollment Mode";
        btn.style.background = "linear-gradient(135deg, #3b82f6, #2563eb)"; // Blue to start
        status.innerText = "Status: Inactive";
        status.style.color = "#94a3b8";
        status.classList.remove("blink");

        // Stop Polling
        stopEnrollmentPolling();
        document.getElementById("new-card-form").style.display = "none";
    }

    // Notify Backend
    try {
        await fetch(`${BACKEND}/api/cards/enroll-mode`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-ROLE": role,
                "X-USER": user
            },
            body: JSON.stringify({ enabled: enrollmentActive })
        });
    } catch (e) {
        console.error("Enrollment check error", e);
    }
}

function startEnrollmentPolling() {
    if (enrollmentPollInterval) clearInterval(enrollmentPollInterval);
    enrollmentPollInterval = setInterval(async () => {
        try {
            const res = await fetch(`${BACKEND}/api/cards/last-scanned`);
            const data = await res.json();

            if (data.uid) {
                // UID Found!
                document.getElementById("scanned-uid").innerText = data.uid;
                document.getElementById("new-card-form").style.display = "block";

                // Stop polling while user enters name
                clearInterval(enrollmentPollInterval);
                document.getElementById("enroll-status").innerText = "Status: Card Detected! Enter Name.";
                document.getElementById("enroll-status").classList.remove("blink");
            }
        } catch (e) {
            console.error("Poll error", e);
        }
    }, 1000); // Check every second
}

function stopEnrollmentPolling() {
    if (enrollmentPollInterval) clearInterval(enrollmentPollInterval);
}

async function saveNewCard() {
    const uid = document.getElementById("scanned-uid").innerText;
    const name = document.getElementById("card-owner").value;

    if (!name) {
        alert("Please enter a name");
        return;
    }

    try {
        const res = await fetch(`${BACKEND}/api/cards/add`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-ROLE": role,
                "X-USER": user
            },
            body: JSON.stringify({ uid: uid, username: name })
        });

        const data = await res.json();
        const msgEl = document.getElementById("card-message");

        if (data.success) {
            msgEl.innerHTML = `<div class="message success">Card added for ${name}!</div>`;

            // Reset
            document.getElementById("card-owner").value = "";
            document.getElementById("new-card-form").style.display = "none";

            // Resume polling for next card
            document.getElementById("enroll-status").innerText = "Status: 📡 Scanning for next card...";
            document.getElementById("enroll-status").classList.add("blink");
            startEnrollmentPolling();
        } else {
            msgEl.innerHTML = `<div class="message error">Error: ${data.error}</div>`;
        }

        setTimeout(() => { msgEl.innerHTML = ""; }, 3000);

    } catch (e) {
        console.error("Save card error", e);
    }
}

// ============ PIN MANAGEMENT ============

function showPINMessage(message, isError = false) {
    const msgEl = document.getElementById("pin-message");
    msgEl.innerHTML = `<div class="message ${isError ? 'error' : 'success'}">${message}</div>`;
    setTimeout(() => { msgEl.innerHTML = ""; }, 5000);
}

async function changePIN() {
    const newPIN = document.getElementById("new-pin").value;

    if (!newPIN || newPIN.length !== 4 || !/^\d{4}$/.test(newPIN)) {
        showPINMessage("PIN must be exactly 4 digits", true);
        return;
    }

    try {
        const res = await fetch(`${BACKEND}/pin`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-ROLE": role,
                "X-USER": user
            },
            body: JSON.stringify({ pin: newPIN })
        });

        const data = await res.json();

        if (res.ok && data.success) {
            showPINMessage("✅ PIN changed successfully");
            document.getElementById("new-pin").value = "";
            document.getElementById("pin-current").innerHTML = "";
        } else {
            showPINMessage(data.error || "Failed to change PIN", true);
        }
    } catch (e) {
        showPINMessage("Backend not reachable", true);
        console.error("PIN change error:", e);
    }
}

async function showCurrentPIN() {
    try {
        const res = await fetch(`${BACKEND}/pin`);
        const data = await res.json();

        if (data.pin) {
            document.getElementById("pin-current").innerHTML =
                `Current PIN: <strong>${data.pin}</strong>`;

            // Hide after 5 seconds for security
            setTimeout(() => {
                document.getElementById("pin-current").innerHTML = "";
            }, 5000);
        }
    } catch (e) {
        showPINMessage("Failed to fetch PIN", true);
        console.error("PIN fetch error:", e);
    }
}

// Only allow numbers in PIN input
document.getElementById("new-pin")?.addEventListener("input", function (e) {
    this.value = this.value.replace(/[^0-9]/g, "");
});

// Logout function
function logout() {
    sessionStorage.clear();
    window.location.href = "index.html";
}

// ============ HARDWARE TEST ============

// Test hardware - blinks LEDs and buzzer
async function testHardware() {
    const statusDiv = document.getElementById("hardware-status");
    const greenLed = document.getElementById("led-green");
    const redLed = document.getElementById("led-red");
    const buzzer = document.getElementById("buzzer-icon");

    statusDiv.innerText = "Testing...";

    try {
        // Call backend to test hardware
        const res = await fetch(`${BACKEND}/hardware/test`, { method: "POST" });

        // Animate LEDs locally for visual feedback
        greenLed.classList.add("blink");
        redLed.classList.add("blink");
        buzzer.classList.add("on");

        // Stop animation after 2 seconds
        setTimeout(() => {
            greenLed.classList.remove("blink");
            redLed.classList.remove("blink");
            buzzer.classList.remove("on");
            refreshStatus(); // Restore actual status
        }, 2000);

        if (res.ok) {
            statusDiv.innerText = "✓ Hardware test sent!";
            showToast("Hardware test triggered!", "success");
        } else {
            statusDiv.innerText = "✗ Test failed";
        }
    } catch (e) {
        // Even if backend fails, show local animation
        greenLed.classList.add("blink");
        redLed.classList.add("blink");
        buzzer.classList.add("on");

        setTimeout(() => {
            greenLed.classList.remove("blink");
            redLed.classList.remove("blink");
            buzzer.classList.remove("on");
        }, 2000);

        statusDiv.innerText = "Local test only (no backend)";
        console.error("Hardware test error:", e);
    }
}

// ============ SIMULATION MODE ============
async function simulateScan(type) {
    const uid = type === 'VALID' ? 'A1B2C3D4' : 'INVALID_CARD';
    console.log(`Simulating scan: ${uid}`);

    try {
        const res = await fetch(`${BACKEND}/api/simulate/scan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uid: uid })
        });
        const data = await res.json();

        if (data.success) {
            showToast(type === 'VALID' ? "✅ Valid Card Scanned" : "⛔ Invalid Card Scanned",
                type === 'VALID' ? "success" : "error");
            refreshStatus();
        }
    } catch (e) {
        console.error("Simulation error:", e);
    }
}

async function simulatePin(type) {
    const pin = type === 'CORRECT' ? '1234' : '9999'; // Default correct PIN is 1234
    console.log(`Simulating PIN: ${pin}`);

    try {
        const res = await fetch(`${BACKEND}/api/simulate/pin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin: pin })
        });
        const data = await res.json();

        if (data.success) {
            showToast(type === 'CORRECT' ? "✅ Correct PIN Entered" : "❌ Wrong PIN Entered",
                type === 'CORRECT' ? "success" : "error");
            refreshStatus();
        }
    } catch (e) {
        console.error("Simulation error:", e);
    }
}

// Fetch hardware status from backend & Toggle Sim Panel
async function fetchHardwareStatus() {
    try {
        const res = await fetch(`${BACKEND}/hardware/status?lock_id=${lockId}`);
        if (res.ok) {
            const data = await res.json();
            const statusDiv = document.getElementById("hardware-status");
            const simPanel = document.getElementById("sim-panel");

            if (data.connected) {
                statusDiv.innerText = "✓ Hardware Connected";
                statusDiv.style.color = "#4ade80";
                simPanel.style.display = "none";
            } else {
                statusDiv.innerText = "✗ Hardware Disconnected (Simulation Active)";
                statusDiv.style.color = "#f472b6";
                simPanel.style.display = "block";
            }
        }
    } catch (e) {
        console.error("Hardware status error:", e);
    }
}

// Fetch and display activity logs
async function fetchLogs() {
    const logList = document.getElementById("log-list");
    if (!logList) return;

    try {
        const res = await fetch(`${BACKEND}/logs`);
        if (!res.ok) throw new Error("Failed to fetch logs");

        const logs = await res.json();

        if (logs.length === 0) {
            logList.innerHTML = '<li class="log-item" style="justify-content:center; opacity:0.5;">No logs available</li>';
            return;
        }

        logList.innerHTML = logs.map(log => {
            const time = log.time ? new Date(log.time).toLocaleString() : "Unknown time";
            const isIntruder = log.log_type === "intruder" || log.message.includes("INTRUDER");

            // Check if log contains photo path
            const photoMatch = log.message.match(/Photo: (.+\.jpg)/);
            const photoPath = photoMatch ? photoMatch[1] : null;

            let logClass = "log-item";
            let icon = "📝";

            if (isIntruder) {
                logClass += " log-intruder";
                icon = "🚨";
            } else if (log.message.includes("unlocked") || log.message.includes("OPEN")) {
                icon = "🔓";
            } else if (log.message.includes("locked") || log.message.includes("LOCK")) {
                icon = "🔒";
            } else if (log.message.includes("Invalid") || log.message.includes("Wrong")) {
                icon = "⛔";
            }

            let photoHtml = "";
            if (photoPath) {
                // Clean message by removing photo path
                const cleanMsg = log.message.replace(` | Photo: ${photoPath}`, "");
                photoHtml = `<a href="${BACKEND}/${photoPath}" target="_blank" style="color:#f472b6; margin-left:0.5rem;">📷 View Photo</a>`;
                return `<li class="${logClass}">
                    <span class="log-time">${time}</span>
                    <span class="log-msg">${icon} ${cleanMsg}${photoHtml}</span>
                </li>`;
            }

            return `<li class="${logClass}">
                <span class="log-time">${time}</span>
                <span class="log-msg">${icon} ${log.message}</span>
            </li>`;
        }).join("");

    } catch (e) {
        console.error("Logs fetch error:", e);
        logList.innerHTML = '<li class="log-item" style="justify-content:center; opacity:0.5;">Failed to load logs</li>';
    }
}

// Initial status fetch and auto-refresh
refreshStatus();
fetchHardwareStatus();
fetchLogs();
setInterval(refreshStatus, 2000); // Faster refresh for smoother sim
setInterval(fetchHardwareStatus, 5000);
setInterval(fetchLogs, 5000); // Refresh logs every 5 seconds

