(() => {
    const panel = document.getElementById("provider-location-sharing");
    if (!panel) return;

    const locationUrl = panel.dataset.locationUrl;
    const availabilityUrl = panel.dataset.availabilityUrl;
    const message = document.getElementById("gps-message");
    const onlineButton = document.getElementById("online-button");
    const retryButton = document.getElementById("location-retry");
    const hasActiveDelivery = panel.dataset.activeDelivery === "true";
    let isOnline = panel.dataset.isOnline === "true";
    let watchId = null;
    let lastSentAt = 0;
    let locationRequestInProgress = false;
    let sharingStarted = false;

    function getCookie(name) {
        const item = document.cookie
            .split("; ")
            .find(row => row.startsWith(name + "="));
        return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
    }

    async function postJson(url, payload) {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify(payload)
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Request failed");
        return data;
    }

    async function sendPosition(position) {
        if (locationRequestInProgress || Date.now() - lastSentAt < 3000) return;
        lastSentAt = Date.now();
        locationRequestInProgress = true;
        try {
            await postJson(locationUrl, {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude
            });
            message.textContent = hasActiveDelivery
                ? "Live location is being shared for your active delivery."
                : "You are online and sharing your live location.";
            retryButton.hidden = true;
        } catch (error) {
            message.textContent = "Could not update location: " + error.message;
            retryButton.hidden = false;
        } finally {
            locationRequestInProgress = false;
        }
    }

    function onLocationError(error) {
        let detail = "Allow location access in your browser settings, then retry.";
        if (error && error.code === error.TIMEOUT) {
            detail = "GPS is taking too long. Keep this page open and retry.";
        }
        message.textContent = "Location sharing is paused. " + detail;
        retryButton.hidden = false;
    }

    function startGps() {
        if (sharingStarted) return;
        if (!navigator.geolocation) {
            message.textContent = "This browser does not support GPS location sharing.";
            retryButton.hidden = false;
            return;
        }
        sharingStarted = true;
        retryButton.hidden = true;
        message.textContent = "Waiting for your device GPS location...";
        watchId = navigator.geolocation.watchPosition(
            sendPosition,
            onLocationError,
            {enableHighAccuracy: true, maximumAge: 3000, timeout: 15000}
        );
    }

    function stopGps() {
        if (watchId !== null && navigator.geolocation) {
            navigator.geolocation.clearWatch(watchId);
        }
        watchId = null;
        sharingStarted = false;
    }

    if (onlineButton) {
        onlineButton.textContent = isOnline ? "Go Offline" : "Go Online";
        onlineButton.addEventListener("click", async () => {
            onlineButton.disabled = true;
            try {
                const nextOnline = !isOnline;
                if (nextOnline) {
                    if (!navigator.geolocation) {
                        throw new Error("GPS is not supported in this browser.");
                    }
                    await new Promise((resolve, reject) => {
                        navigator.geolocation.getCurrentPosition(resolve, reject, {
                            enableHighAccuracy: true,
                            timeout: 15000
                        });
                    });
                }
                await postJson(availabilityUrl, {online: nextOnline});
                isOnline = nextOnline;
                onlineButton.textContent = isOnline ? "Go Offline" : "Go Online";
                if (isOnline || hasActiveDelivery) {
                    startGps();
                } else {
                    stopGps();
                    message.textContent = "You are offline. Location sharing has stopped.";
                }
            } catch (error) {
                message.textContent = "Could not change availability: " + error.message;
            } finally {
                onlineButton.disabled = false;
            }
        });
    }

    retryButton?.addEventListener("click", () => {
        if (!hasActiveDelivery && !isOnline) {
            message.textContent = "Accept a job or go online before sharing location.";
            return;
        }
        stopGps();
        startGps();
    });

    if (hasActiveDelivery || isOnline) startGps();
    else if (!message.textContent.trim()) {
        message.textContent = "Accept a job to start live delivery tracking.";
    }

    window.addEventListener("pagehide", stopGps);
})();
