const BACKEND = "http://127.0.0.1:5000";

async function login() {
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();

    if (!username || !password) {
        alert("Username and password required");
        return;
    }

    try {
        const res = await fetch(`${BACKEND}/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        if (!res.ok) {
            alert("Invalid username or password");
            return;
        }

        const data = await res.json();

        sessionStorage.setItem("user", data.username);
        sessionStorage.setItem("role", data.role);

        window.location.href = "dashboard.html";

    } catch (err) {
        alert("Backend not running");
        console.error(err);
    }
}
