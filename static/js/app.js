// Request notification permission
// ----- NOTIFICATION PERMISSION -----
function requestNotificationPermission() {
    if (!("Notification" in window)) {
        alert("This browser does not support notifications.");
        return;
    }

    Notification.requestPermission().then(function (permission) {
        if (permission === "granted") {
            alert("Notifications enabled ✅");
        } else if (permission === "denied") {
            alert("Notifications are blocked. You can change this in your browser settings.");
        }
    });
}

// Simple manual test (still useful)
function sendTestNotification() {
    if (!("Notification" in window)) {
        alert("This browser does not support notifications.");
        return;
    }

    if (Notification.permission !== "granted") {
        alert("Please enable notifications first.");
        return;
    }

    new Notification("Trading alert 🔔", {
        body: "This is a test notification from your trading app.",
        icon: "/static/icons/icon-192.png"
    });
}

// ----- LIVE SIGNAL POLLING -----

// Store last known signal per symbol, so we only alert on changes
let lastSignals = {};

async function checkLiveSignals() {
    if (!("Notification" in window)) {
        console.log("Notifications not supported in this browser.");
        return;
    }

    if (Notification.permission !== "granted") {
        console.log("Notifications not granted yet.");
        return;
    }

    try {
        const response = await fetch("/api/live-signals");
        if (!response.ok) {
            console.log("Error fetching live signals:", response.status);
            return;
        }

        const data = await response.json();
        const signals = data.signals || [];

        signals.forEach((row) => {
            const symbol = row.symbol;
            const signal = row.signal;  // "BUY", "SELL", or "none"
            const price = row.price;
            const time = row.time;

            // Skip if no actionable signal
            if (signal !== "BUY" && signal !== "SELL") {
                return;
            }

            const prev = lastSignals[symbol];

            // Only notify if this symbol's signal changed since last check
            if (!prev || prev !== signal) {
                // Save new state
                lastSignals[symbol] = signal;

                // Fire notification
                new Notification(`Signal: ${signal} on ${symbol}`, {
                    body: `Price: ${price} at ${time}`,
                    icon: "/static/icons/icon-192.png"
                });
            }
        });
    } catch (err) {
        console.log("Error during live signal poll:", err);
    }
}

// Start polling when the page loads
function startSignalPolling() {
    // Run once right away
    checkLiveSignals();

    // Then every 60 seconds
    setInterval(checkLiveSignals, 60 * 1000);
}

// Expose functions to HTML
window.requestNotificationPermission = requestNotificationPermission;
window.sendTestNotification = sendTestNotification;

// When the page is fully loaded, start polling
window.addEventListener("load", function () {
    startSignalPolling();
    console.log("Trading App JS loaded, live signal polling started.");
});
