document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("fuelRequestForm");
    const locationBtn = document.getElementById("getLocationBtn");
    const locationStatus = document.getElementById("locationStatus");
    const addressField = document.getElementById("address");
    const latitudeField = document.getElementById("latitude");
    const longitudeField = document.getElementById("longitude");
    const dateInput = document.getElementById("deliveryDate");
    const formMessage = document.getElementById("formMessage");
    const submitButton = document.getElementById("submitRequestBtn");
    const geoapifyKey = document.querySelector(".fuel-page")?.dataset.geoapifyKey || "";

    if (dateInput) {
        const today = new Date();
        const localToday = [
            today.getFullYear(),
            String(today.getMonth() + 1).padStart(2, "0"),
            String(today.getDate()).padStart(2, "0")
        ].join("-");
        dateInput.min = localToday;
    }

    if (locationBtn && locationStatus && addressField && latitudeField && longitudeField) {
        locationBtn.addEventListener("click", function () {
            if (!navigator.geolocation) {
                locationStatus.textContent = "Location is not available in this browser. Enter your address manually.";
                return;
            }

            const isLocalHost = ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
            if (!window.isSecureContext && !isLocalHost) {
                locationStatus.textContent = "Your browser requires a secure HTTPS connection to use location. Open this site over HTTPS or use localhost.";
                return;
            }

            const originalButtonHtml = locationBtn.innerHTML;
            locationBtn.disabled = true;
            locationBtn.textContent = "Finding your location...";
            locationStatus.textContent = "Allow location access in your browser when prompted.";

            navigator.geolocation.getCurrentPosition(async function (position) {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;
                const lat = latitude.toFixed(6);
                const lon = longitude.toFixed(6);

                latitudeField.value = lat;
                longitudeField.value = lon;
                locationStatus.textContent = "GPS captured. Looking up the address...";

                let formattedAddress = "";
                if (geoapifyKey) {
                    try {
                        const url = new URL("https://api.geoapify.com/v1/geocode/reverse");
                        url.search = new URLSearchParams({
                            lat: String(latitude),
                            lon: String(longitude),
                            format: "json",
                            limit: "1",
                            apiKey: geoapifyKey
                        });
                        const response = await fetch(url, { signal: AbortSignal.timeout(8000) });
                        if (!response.ok) {
                            throw new Error("Address lookup failed");
                        }
                        const result = await response.json();
                        formattedAddress = result.results?.[0]?.formatted || "";
                    } catch (error) {
                        // Keep the GPS coordinates even when reverse geocoding is unavailable.
                    }
                }

                if (formattedAddress) {
                    addressField.value = formattedAddress;
                    locationStatus.textContent = "Current location and address added. Check the address and add a nearby landmark if needed.";
                } else {
                    if (!addressField.value.trim()) {
                        addressField.value = `Current location (GPS: ${lat}, ${lon})`;
                    }
                    locationStatus.textContent = "Current GPS coordinates saved. Add or confirm your full delivery address and nearby landmark.";
                }

                locationBtn.disabled = false;
                locationBtn.innerHTML = originalButtonHtml;
            }, function (error) {
                const messages = {
                    1: "Location permission was denied. Allow location access for this site in your browser settings, then try again.",
                    2: "Your device could not determine its location. Check that Location Services are on and try again.",
                    3: "Location lookup timed out. Move to an area with better GPS or network reception and try again."
                };
                locationStatus.textContent = messages[error.code] || "Could not get your location. Enter your address manually.";
                locationBtn.disabled = false;
                locationBtn.innerHTML = originalButtonHtml;
            }, {
                enableHighAccuracy: true,
                timeout: 20000,
                maximumAge: 30000
            });
        });
    }

    if (form) {
        form.addEventListener("submit", function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                form.reportValidity();
                return;
            }

            const phone = document.getElementById("phone");
            if (phone && !/^[6-9]\d{9}$/.test(phone.value.trim())) {
                event.preventDefault();
                if (formMessage) {
                    formMessage.textContent = "Enter a valid 10-digit Indian mobile number.";
                    formMessage.classList.remove("info");
                    formMessage.classList.add("show", "error");
                }
                phone.focus();
                return;
            }

            if (formMessage) {
                formMessage.textContent = "Submitting your fuel request...";
                formMessage.classList.remove("error");
                formMessage.classList.add("show", "info");
            }
            if (submitButton) {
                submitButton.disabled = true;
                const buttonText = submitButton.querySelector(".button-text");
                if (buttonText) {
                    buttonText.textContent = "Submitting...";
                }
            }
        });
    }
});
