
document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("sidebar");
    const menuToggle = document.getElementById("menuToggle");
    const toast = document.getElementById("dashboardToast");

    // Mobile navigation
    if (sidebar && menuToggle) {
        menuToggle.addEventListener("click", () => {
            const isOpen = sidebar.classList.toggle("open");
            menuToggle.setAttribute("aria-expanded", String(isOpen));
        });

        document.addEventListener("click", (event) => {
            if (
                window.innerWidth <= 900 &&
                sidebar.classList.contains("open") &&
                !sidebar.contains(event.target) &&
                !menuToggle.contains(event.target)
            ) {
                sidebar.classList.remove("open");
                menuToggle.setAttribute("aria-expanded", "false");
            }
        });

        sidebar.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => {
                if (window.innerWidth <= 900) {
                    sidebar.classList.remove("open");
                    menuToggle.setAttribute("aria-expanded", "false");
                }
            });
        });
    }

    // Reveal sections when they enter the viewport
    const revealElements = document.querySelectorAll(".reveal");

    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver(
            (entries, currentObserver) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("visible");
                        currentObserver.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.12 }
        );

        revealElements.forEach((element, index) => {
            element.style.transitionDelay = `${Math.min(index * 70, 280)}ms`;
            observer.observe(element);
        });
    } else {
        revealElements.forEach((element) => {
            element.classList.add("visible");
        });
    }

    // Highlight the selected sidebar section
    const navLinks = document.querySelectorAll(
        '.sidebar-nav a[href^="#"]'
    );

    const sections = [...navLinks]
        .map((link) => document.querySelector(link.getAttribute("href")))
        .filter(Boolean);

    if ("IntersectionObserver" in window && sections.length) {
        const sectionObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (!entry.isIntersecting) return;

                    navLinks.forEach((link) => {
                        link.classList.toggle(
                            "active",
                            link.getAttribute("href") === `#${entry.target.id}`
                        );
                    });
                });
            },
            { rootMargin: "-25% 0px -60% 0px" }
        );

        sections.forEach((section) => sectionObserver.observe(section));
    }

    // Small toast helper for future actions
    window.showFuelFixToast = (message) => {
        if (!toast) return;

        toast.textContent = message;
        toast.classList.add("show");

        window.clearTimeout(window.fuelFixToastTimer);

        window.fuelFixToastTimer = window.setTimeout(() => {
            toast.classList.remove("show");
        }, 3000);
    };
});
