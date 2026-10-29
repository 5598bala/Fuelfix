
/* ==========================================
   FUELFIX CUSTOMER LOGIN - FUNCTIONALITY
========================================== */

(() => {
    "use strict";

    function initializeCustomerLogin() {
        const root = document.getElementById("customer-login");

        if (!root) return;

        const phoneInput = document.getElementById("phone");
        const otpInput = document.getElementById("otp");
        const sendBtn = document.getElementById("send-btn");
        const verifyBtn = document.getElementById("verify-btn");
        const otpArea = document.getElementById("otp-area");
        const message = document.getElementById("message");

        const csrfInput = document.querySelector(
            "#csrf-form [name='csrfmiddlewaretoken']"
        );

        const sendUrl = root.dataset.sendUrl;
        const verifyUrl = root.dataset.verifyUrl;
        const dashboardUrl = root.dataset.dashboardUrl;

        if (
            !phoneInput || !otpInput || !sendBtn ||
            !verifyBtn || !otpArea || !message
        ) {
            console.error("FuelFix login elements are missing.");
            return;
        }

        let otpSent = false;
        let resendTimer = null;

        /* Display accessible status messages */
        function showMessage(text, type = "success") {
            message.textContent = text;

            message.classList.remove(
                "message-success",
                "message-error",
                "message-info"
            );

            message.classList.add(`message-${type}`);
            message.setAttribute("role", type === "error" ? "alert" : "status");
        }

        /* Button loading state */
        function setButtonLoading(button, loading, text) {
            const label = button.querySelector(".btn-text");

            if (loading) {
                button.dataset.originalText =
                    label ? label.textContent : button.textContent.trim();

                if (label) label.textContent = text;

                button.disabled = true;
                button.setAttribute("aria-busy", "true");
            } else {
                if (label && button.dataset.originalText) {
                    label.textContent = button.dataset.originalText;
                }

                button.disabled = false;
                button.removeAttribute("aria-busy");
            }
        }

        /* Accept phone autofill/paste values with the Indian +91 prefix. */
        function normalizePhone(value) {
            let digits = String(value || "").replace(/\D/g, "");
            if (digits.length === 12 && digits.startsWith("91")) {
                digits = digits.slice(2);
            }
            return digits;
        }

        /* Keep the numeric keypad available on mobile phones. */
        phoneInput.addEventListener("input", () => {
            phoneInput.value = normalizePhone(phoneInput.value);

            phoneInput.setCustomValidity("");
        });

        /* Restrict OTP input to six digits */
        otpInput.addEventListener("input", () => {
            otpInput.value = otpInput.value
                .replace(/\D/g, "")
                .slice(0, 6);
        });

        /* Keyboard shortcut: Enter in phone field */
        phoneInput.addEventListener("keydown", event => {
            if (event.key === "Enter") {
                event.preventDefault();
                sendBtn.click();
            }
        });

        /* Keyboard shortcut: Enter in OTP field */
        otpInput.addEventListener("keydown", event => {
            if (event.key === "Enter") {
                event.preventDefault();
                verifyBtn.click();
            }
        });

        /* Send JSON request to Django */
        async function postJson(url, payload) {
            if (!csrfInput) {
                throw new Error(
                    "Security token missing. Refresh the page and try again."
                );
            }

            if (!url) {
                throw new Error("Login endpoint is not configured.");
            }

            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfInput.value
                },
                body: JSON.stringify(payload),
                credentials: "same-origin"
            });

            let data;

            try {
                data = await response.json();
            } catch {
                throw new Error(
                    "Unexpected server response. Please try again."
                );
            }

            if (!response.ok || !data.ok) {
                const error = new Error(
                    data.error || "Request failed. Please try again."
                );
                error.wait = data.wait;
                throw error;
            }

            return data;
        }

        function startResendCountdown(seconds) {
            if (resendTimer !== null) clearInterval(resendTimer);

            let remaining = Math.max(1, Number(seconds) || 30);
            const label = sendBtn.querySelector(".btn-text");
            sendBtn.disabled = true;
            sendBtn.setAttribute("aria-disabled", "true");

            const update = () => {
                if (label) label.textContent = `Resend OTP in ${remaining}s`;
                if (remaining <= 0) {
                    clearInterval(resendTimer);
                    resendTimer = null;
                    sendBtn.disabled = false;
                    sendBtn.removeAttribute("aria-disabled");
                    if (label) label.textContent = "Resend OTP";
                    return;
                }
                remaining -= 1;
            };

            update();
            resendTimer = setInterval(update, 1000);
        }

        /* SEND OTP */
        sendBtn.addEventListener("click", async () => {
            if (sendBtn.disabled) return;

            const phone = normalizePhone(phoneInput.value);

            if (!/^\d{10}$/.test(phone)) {
                showMessage(
                    "Please enter a valid 10-digit mobile number.",
                    "error"
                );

                phoneInput.focus();
                phoneInput.closest(".input-shell")?.classList.add("input-error");
                return;
            }

            phoneInput.value = phone;
            phoneInput.closest(".input-shell")?.classList.remove("input-error");

            setButtonLoading(sendBtn, true, "Sending OTP...");
            showMessage("Sending your verification code...", "info");

            try {
                const data = await postJson(sendUrl, {
                    phone: phone
                });

                otpSent = true;
                otpInput.value = "";
                otpArea.hidden = false;

                setButtonLoading(sendBtn, false);
                const sendLabel = sendBtn.querySelector(".btn-text");
                if (sendLabel) sendLabel.textContent = "OTP request accepted ✓";
                startResendCountdown(data.resend_in || 30);

                showMessage(
                    data.message || "OTP request accepted. Please check your phone.",
                    "success"
                );

                otpInput.focus({
                    preventScroll: false
                });

            } catch (error) {
                setButtonLoading(sendBtn, false);
                if (error.wait) startResendCountdown(error.wait);
                showMessage(error.message, "error");
            }
        });

        /* VERIFY OTP */
        verifyBtn.addEventListener("click", async () => {
            if (verifyBtn.disabled) return;

            if (!otpSent) {
                showMessage("Please request an OTP first.", "error");
                return;
            }

            const phone = normalizePhone(phoneInput.value);
            const otp = otpInput.value.trim();

            if (!/^\d{10}$/.test(phone)) {
                showMessage("Please enter a valid mobile number.", "error");
                phoneInput.focus();
                return;
            }

            if (!/^\d{6}$/.test(otp)) {
                showMessage("Please enter the complete 6-digit OTP.", "error");
                otpInput.focus();
                return;
            }

            setButtonLoading(verifyBtn, true, "Verifying...");
            showMessage("Verifying your OTP securely...", "info");

            try {
                const data = await postJson(verifyUrl, {
                    phone: phone,
                    otp: otp
                });

                showMessage("Verification successful. Redirecting...", "success");

                const destination = data.redirect || dashboardUrl;

                if (!destination) {
                    throw new Error("Login succeeded, but no redirect URL was configured.");
                }

                window.location.assign(destination);

            } catch (error) {
                showMessage(error.message, "error");
                setButtonLoading(verifyBtn, false);
                otpInput.focus();
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initializeCustomerLogin
        );
    } else {
        initializeCustomerLogin();
    }
})();
