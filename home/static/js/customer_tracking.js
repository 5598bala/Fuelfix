(() => {
    "use strict";

    const page = document.getElementById("tracking-page");
    if (!page) return;

    const dataUrl = page.dataset.dataUrl;
    const apiKey = page.dataset.geoapifyKey || "";
    const locationStatus = document.getElementById("location-status");
    const statusLabel = document.getElementById("job-status");
    const coordinatesLabel = document.getElementById("provider-coordinates");
    const openMapLink = document.getElementById("provider-map-link");
    const mapLoadStatus = document.getElementById("map-load-status");
    const mapElement = document.getElementById("tracking-map");
    const destinationLat = Number(page.dataset.destinationLat);
    const destinationLon = Number(page.dataset.destinationLon);
    const hasDestination = Number.isFinite(destinationLat) &&
        Number.isFinite(destinationLon) &&
        destinationLat >= -90 && destinationLat <= 90 &&
        destinationLon >= -180 && destinationLon <= 180 &&
        page.dataset.destinationLat !== "" && page.dataset.destinationLon !== "";
    const destination = hasDestination ? [destinationLat, destinationLon] : null;

    let map = null;
    let providerMarker = null;
    let firstLocation = true;
    let requestInProgress = false;
    let refreshTimer = null;
    let tileErrorShown = false;

    if (mapElement && apiKey && window.L) {
        map = L.map(mapElement, {scrollWheelZoom: false});
        map.setView(destination || [11.0168, 76.9558], destination ? 14 : 12);

        const tiles = L.tileLayer(
            `https://maps.geoapify.com/v1/tile/osm-carto/{z}/{x}/{y}.png?apiKey=${encodeURIComponent(apiKey)}`,
            {
                apiKey,
                maxZoom: 20,
                attribution: 'Powered by <a href="https://www.geoapify.com/" target="_blank" rel="noopener">Geoapify</a> | <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap contributors</a>'
            }
        ).addTo(map);

        tiles.on("tileerror", () => {
            if (tileErrorShown || !mapLoadStatus) return;
            tileErrorShown = true;
            mapLoadStatus.textContent =
                "Map tiles could not load. Live coordinates are still updating below.";
        });
        tiles.on("tileload", () => {
            tileErrorShown = false;
            if (mapLoadStatus) mapLoadStatus.textContent = "";
        });

        if (destination) {
            L.marker(destination).addTo(map).bindPopup("Your delivery address");
        }
        requestAnimationFrame(() => map.invalidateSize({pan: false}));
    } else if (mapElement && apiKey && mapLoadStatus) {
        mapLoadStatus.textContent = "The map could not start. Provider coordinates will still update below.";
    }

    function updateStatusMessage(data, hasLocation) {
        if (data.status === "delivered") {
            locationStatus.textContent = "Your delivery is complete.";
        } else if (data.status === "accepted" || data.status === "out_for_delivery") {
            locationStatus.textContent = hasLocation
                ? "Provider location is live. Updated " +
                    (data.location_updated
                        ? new Date(data.location_updated).toLocaleTimeString()
                        : "just now") + "."
                : "The provider accepted your request. Waiting for a fresh GPS location...";
        } else if (data.status === "assigned") {
            locationStatus.textContent = "Your provider has been assigned. Live tracking begins when they accept.";
        } else if (data.status === "rejected") {
            locationStatus.textContent = "The provider could not take this request. We are finding another provider.";
        } else {
            locationStatus.textContent = "Waiting for a provider to accept your request.";
        }
    }

    async function refreshTracking() {
        if (requestInProgress || document.hidden) return;
        requestInProgress = true;

        try {
            const response = await fetch(dataUrl, {
                headers: {"X-Requested-With": "XMLHttpRequest"},
                cache: "no-store",
                credentials: "same-origin"
            });
            if (!response.ok) throw new Error("Could not load tracking data");

            const data = await response.json();
            statusLabel.textContent = data.status_display || data.status.replaceAll("_", " ");
            const hasLocation = Number.isFinite(data.provider_latitude) &&
                Number.isFinite(data.provider_longitude);
            updateStatusMessage(data, hasLocation);

            if (!hasLocation) {
                coordinatesLabel.textContent = "Waiting for a fresh GPS location…";
                openMapLink.hidden = true;
                if (map && providerMarker) {
                    map.removeLayer(providerMarker);
                    providerMarker = null;
                    firstLocation = true;
                }
            } else {
                const latitude = data.provider_latitude;
                const longitude = data.provider_longitude;
                const point = [latitude, longitude];
                coordinatesLabel.textContent = `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
                openMapLink.href = `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`;
                openMapLink.hidden = false;

                if (map) {
                    if (!providerMarker) {
                        providerMarker = L.marker(point).addTo(map).bindPopup("Your FuelFix provider");
                    } else {
                        providerMarker.setLatLng(point);
                    }

                    if (firstLocation) {
                        const points = destination ? [destination, point] : [point];
                        map.fitBounds(L.latLngBounds(points), {padding: [30, 30], maxZoom: 15});
                        firstLocation = false;
                    }
                }
            }

            if (data.status === "delivered" && refreshTimer !== null) {
                clearInterval(refreshTimer);
                refreshTimer = null;
            }
        } catch (error) {
            locationStatus.textContent = "Tracking is temporarily unavailable. Retrying...";
        } finally {
            requestInProgress = false;
        }
    }

    window.addEventListener("resize", () => {
        if (map) map.invalidateSize({pan: false});
    });
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) {
            if (map) map.invalidateSize({pan: false});
            refreshTracking();
        }
    });

    refreshTracking();
    refreshTimer = window.setInterval(refreshTracking, 4000);
})();
