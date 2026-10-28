(() => {
    const root = document.documentElement;
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');

    function applyTheme(theme, save = false) {
        const isDark = theme === "dark";
        root.dataset.theme = isDark ? "dark" : "light";
        root.style.colorScheme = isDark ? "dark" : "light";
        if (metaThemeColor) {
            metaThemeColor.setAttribute("content", isDark ? "#0b1220" : "#f5f8fc");
        }

        document.querySelectorAll("[data-theme-toggle]").forEach(button => {
            const icon = button.querySelector(".theme-toggle-icon");
            const label = button.querySelector(".theme-toggle-label");
            const nextTheme = isDark ? "light" : "dark";
            const action = `Switch to ${nextTheme} theme`;
            if (icon) icon.textContent = isDark ? "☀" : "☾";
            if (label) label.textContent = isDark ? "Light" : "Dark";
            button.setAttribute("aria-label", action);
            button.setAttribute("title", action);
            button.setAttribute("aria-pressed", String(isDark));
        });

        if (save) {
            try {
                localStorage.setItem("fuelfix-theme", isDark ? "dark" : "light");
            } catch (error) {
                // Keep the selected theme for this page if storage is unavailable.
            }
        }
    }

    applyTheme(root.dataset.theme === "dark" ? "dark" : "light");
    document.querySelectorAll("[data-theme-toggle]").forEach(button => {
        button.addEventListener("click", () => {
            applyTheme(root.dataset.theme === "dark" ? "light" : "dark", true);
        });
    });
})();
