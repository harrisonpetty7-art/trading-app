// Request notification permission
function requestNotificationPermission() {
    if (!("Notification" in window)) {
        alert("This browser does not support notifications.");
        return;
    }

    Notification.requestPermission().then(function(permission) {
        if (permission === "granted") {
            alert("Notifications enabled ✅");
        } else if (permission === "denied") {
            alert("Notifications are blocked. You can change this in your browser settings.");
        }
    });
}

// Send a test notification
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
        icon: "/static/icons/icon-192.png" // if browser supports it
    });
}

// Expose functions to the HTML
window.requestNotificationPermission = requestNotificationPermission;
window.sendTestNotification = sendTestNotification;

console.log("Trading App JS loaded");

