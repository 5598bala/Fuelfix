
document.addEventListener("DOMContentLoaded", () => {
    const loginTab = document.getElementById("loginTab");
    const registerTab = document.getElementById("registerTab");
    const tabs = document.querySelector(".auth-tabs");
    const indicator = document.getElementById("tabIndicator");

    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");

    const formTitle = document.getElementById("formTitle");
    const formSubtitle = document.getElementById("formSubtitle");

    function setMode(mode) {
        const isRegister = mode === "register";

        loginForm.classList.toggle("hidden", isRegister);
        registerForm.classList.toggle("hidden", !isRegister);

        loginTab.classList.toggle("active", !isRegister);
        registerTab.classList.toggle("active", isRegister);
        tabs.classList.toggle("register-mode", isRegister);

        loginTab.setAttribute("aria-pressed", String(!isRegister));
        registerTab.setAttribute("aria-pressed", String(isRegister));

        formTitle.innerHTML = isRegister
            ? "Become a partner<span>.</span>"
            : "Welcome back<span>.</span>";

        formSubtitle.textContent = isRegister
            ? "Create your account to start your FuelFix journey."
            : "Sign in to manage your service requests.";
    }

    loginTab.addEventListener("click", () => setMode("login"));
    registerTab.addEventListener("click", () => setMode("register"));

    document.querySelectorAll("[data-mode]").forEach(button => {
        button.addEventListener("click", () => {
            setMode(button.dataset.mode);
        });
    });

    // Show / hide passwords
    document.querySelectorAll(".password-toggle").forEach(button => {
        button.addEventListener("click", () => {
            const field = document.getElementById(button.dataset.target);
            const showing = field.type === "text";

            field.type = showing ? "password" : "text";
            button.textContent = showing ? "Show" : "Hide";
            button.setAttribute(
                "aria-label",
                showing ? "Show password" : "Hide password"
            );
        });
    });

    // Registration validation
    registerForm.addEventListener("submit", event => {
        const password = document.getElementById("registerPassword");
        const confirmPassword = document.getElementById("confirmPassword");
        const phone = document.getElementById("phone");

        if (!/^[6-9]\d{9}$/.test(phone.value.trim())) {
            event.preventDefault();
            phone.setCustomValidity(
                "Enter a valid 10-digit Indian mobile number."
            );
            phone.reportValidity();
            phone.setCustomValidity("");
            return;
        }

        if (password.value.length < 8) {
            event.preventDefault();
            password.setCustomValidity(
                "Password must contain at least 8 characters."
            );
            password.reportValidity();
            password.setCustomValidity("");
            return;
        }

        if (password.value !== confirmPassword.value) {
            event.preventDefault();
            confirmPassword.setCustomValidity("Passwords do not match.");
            confirmPassword.reportValidity();
            confirmPassword.setCustomValidity("");
        }
    });

    // Clear custom errors as the user edits fields
    document.querySelectorAll("input").forEach(input => {
        input.addEventListener("input", () => input.setCustomValidity(""));
    });

    setMode(tabs.dataset.initialMode || "login");
});
