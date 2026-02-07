const BACKEND = "http://127.0.0.1:5000";
const list = document.getElementById("log-list");

async function loadLogs() {
    try {
        const res = await fetch(`${BACKEND}/logs`);

        if (!res.ok) throw new Error("Failed to fetch logs");

        const logs = await res.json();

        // Clear current list
        list.innerHTML = "";

        if (logs.length === 0) {
            list.innerHTML = '<li class="empty-state">No logs yet. Actions will appear here.</li>';
            return;
        }

        logs.forEach(log => {
            const li = document.createElement("li");

            // Format timestamp
            const timestamp = log.time ? new Date(log.time).toLocaleString() : "Unknown time";

            // Create structured log entry
            li.innerHTML = `
                <div class="timestamp">${timestamp}</div>
                <div class="message">${log.message}</div>
            `;

            // Apply color coding based on message content
            if (log.message && log.message.includes("INTRUDER")) {
                li.classList.add("log-intruder");
            } else if (log.message && log.message.includes("ADMIN")) {
                li.classList.add("log-admin");
            } else if (log.message && log.message.includes("USER")) {
                li.classList.add("log-user");
            }

            list.appendChild(li);
        });
    } catch (e) {
        list.innerHTML = '<li class="empty-state" style="color: #f59e0b;">⚠️ Backend not reachable. Make sure the server is running.</li>';
        console.error("Logs fetch error:", e);
    }
}

// Initial load and auto-refresh
loadLogs();
setInterval(loadLogs, 3000);
