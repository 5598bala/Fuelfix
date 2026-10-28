(() => {
    "use strict";

    const loader = document.getElementById("fuelfixPageLoader");
    const root = document.documentElement;

    if (!loader) {
        root.classList.remove("fuelfix-loader-enabled");
        return;
    }

    const startedAt = performance.now();

    function hideLoader() {
        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const minimumDuration = reducedMotion ? 150 : 650;
        const remaining = Math.max(0, minimumDuration - (performance.now() - startedAt));

        window.setTimeout(() => {
            loader.classList.add("is-hidden");
            window.setTimeout(() => {
                root.classList.remove("fuelfix-loader-enabled");
                loader.remove();
            }, 360);
        }, remaining);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", hideLoader, { once: true });
    } else {
        hideLoader();
    }
})();