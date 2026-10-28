(() => {
    const toggle = document.querySelector("[data-sos-open]");
    const dialog = document.getElementById("sosDialog");
    if (!toggle || !dialog) return;
    const closeButton = dialog.querySelector("[data-sos-close]");
    const startButton = dialog.querySelector("[data-sos-start-location]");
    const tools = document.getElementById("sosLocationTools");
    const status = document.getElementById("sosLocationStatus");
    const shareActions = document.getElementById("sosShareActions");
    const shareButton = document.getElementById("sosShareNow");
    const liveLink = document.getElementById("sosLiveLink");
    const smsLink = document.getElementById("sosSendSms");
    const stopButton = document.getElementById("sosStopLocation");
    let watchId = null, heartbeatId = null, lastSentAt = 0, currentShareUrl = "", isSharing = false, latestPosition = null, pendingSave = Promise.resolve();

    function openDialog() {
        dialog.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
        document.body.classList.add("sos-open");
        closeButton.focus();
    }
    function closeDialog() {
        dialog.hidden = true;
        toggle.setAttribute("aria-expanded", "false");
        document.body.classList.remove("sos-open");
        toggle.focus();
    }
    toggle.addEventListener("click", openDialog);
    closeButton.addEventListener("click", closeDialog);
    dialog.addEventListener("click", event => { if (event.target === dialog) closeDialog(); });
    document.addEventListener("keydown", event => { if (event.key === "Escape" && !dialog.hidden) closeDialog(); });

    async function saveLocation(position) {
        latestPosition = position;
        if (!isSharing || Date.now() - lastSentAt < 8000) return;
        lastSentAt = Date.now();
        status.textContent = "Updating your live location…";
        const csrf = document.querySelector("#sosCsrfForm [name=csrfmiddlewaretoken]")?.value || "";
        pendingSave = (async () => {
          try {
            const response = await fetch("/sos/location/update/", {
                method: "POST", credentials: "same-origin",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
                body: JSON.stringify({ latitude: position.coords.latitude, longitude: position.coords.longitude, accuracy: position.coords.accuracy })
            });
            const data = await response.json();
            if (!response.ok || !data.ok) throw new Error(data.error || "Could not save your location.");
            currentShareUrl = data.share_url;
            liveLink.href = currentShareUrl;
            liveLink.hidden = false;
            const supportPhone = dialog.dataset.supportPhone || "";
            smsLink.href = `sms:${supportPhone}?body=${encodeURIComponent(`My FuelFix live location: ${currentShareUrl}`)}`;
            smsLink.hidden = !supportPhone;
            shareActions.hidden = false;
            stopButton.hidden = false;
            status.textContent = "Your live link is ready. Keep this page open while sharing.";
          } catch (error) {
            status.textContent = error.message || "Could not share your location. Please try again.";
          }
        })();
        await pendingSave;
    }
    function startSharing() {
        tools.hidden = false;
        status.textContent = "Requesting your location…";
        if (!navigator.geolocation) { status.textContent = "This browser does not support location sharing."; return; }
        if (watchId !== null) return;
        isSharing = true;
        stopButton.hidden = false;
        watchId = navigator.geolocation.watchPosition(position => { latestPosition = position; saveLocation(position); }, error => {
            const messages = { 1: "Location permission was denied. Allow it in browser settings to share.", 2: "Your location is unavailable. Try again in an open area.", 3: "Location request timed out. Please try again." };
            status.textContent = messages[error.code] || "Could not read your location.";
        }, { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 });
        heartbeatId = window.setInterval(() => { if (latestPosition) saveLocation(latestPosition); }, 20000);
    }
    startButton?.addEventListener("click", startSharing);
    shareButton?.addEventListener("click", async () => {
        if (!currentShareUrl) return;
        if (navigator.share) {
            try { await navigator.share({ title: "FuelFix live location", text: "Follow my live location while I get roadside help.", url: currentShareUrl }); }
            catch (error) { if (error.name !== "AbortError") status.textContent = "Use the links below to share your location."; }
        } else if (navigator.clipboard) {
            try { await navigator.clipboard.writeText(currentShareUrl); status.textContent = "Live link copied. Paste it into a message to FuelFix support."; }
            catch (error) { status.textContent = "Use the links below to share your location."; }
        } else status.textContent = "Use the links below to share your location.";
    });
    stopButton?.addEventListener("click", async () => {
        isSharing = false;
        if (watchId !== null) navigator.geolocation.clearWatch(watchId);
        if (heartbeatId !== null) window.clearInterval(heartbeatId);
        watchId = null;
        heartbeatId = null;
        await pendingSave;
        const csrf = document.querySelector("#sosCsrfForm [name=csrfmiddlewaretoken]")?.value || "";
        try {
            await fetch("/sos/location/stop/", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf }, body: "{}" });
        } finally {
            status.textContent = "Location sharing stopped. The live link is no longer updating.";
            stopButton.hidden = true;
        }
    });
})();
