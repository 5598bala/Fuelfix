document.addEventListener("DOMContentLoaded", function () {
    const card = document.querySelector(".validation-card");
    const statusIcon = document.getElementById("statusIcon");

    if (card) {
        card.classList.add("page-loaded");
    }

    if (statusIcon) {
        statusIcon.setAttribute("aria-live", "polite");
    }

    // Visual feedback only.
    // The server determines authentication and approval status.
    const dashboardLink = document.querySelector(
        'a[href*="provider_dashboard"]'
    );

    if (dashboardLink) {
        dashboardLink.addEventListener("click", function (event) {
            // Do not permit navigation if the server has not rendered
            // the approved state. This is extra UI protection only.
            if (!statusIcon || !statusIcon.classList.contains("approved")) {
                event.preventDefault();
            }
        });
    }
});