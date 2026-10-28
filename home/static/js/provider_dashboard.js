
document.addEventListener("DOMContentLoaded", () => {

    // Display today's date.
    const dateElement = document.getElementById("currentDate");

    if (dateElement) {
        dateElement.textContent = new Intl.DateTimeFormat(undefined, {
            weekday: "short",
            day: "2-digit",
            month: "short",
            year: "numeric"
        }).format(new Date());
    }

    // Reveal elements when they enter the screen.
    const revealElements = document.querySelectorAll(".reveal");

    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver((entries, currentObserver) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("visible");
                    currentObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });

        revealElements.forEach((element, index) => {
            element.style.transitionDelay =
                `${(index % 4) * 70}ms`;

            observer.observe(element);
        });
    } else {
        revealElements.forEach(element => {
            element.classList.add("visible");
        });
    }

    // Animated statistics.
    // Values stay at zero until connected to Django database data.
    document.querySelectorAll("[data-count]").forEach(element => {
        const target = Number(element.dataset.count || 0);
        const startTime = performance.now();
        const duration = 900;

        function animate(now) {
            const progress = Math.min(
                (now - startTime) / duration, 1
            );

            const eased = 1 - Math.pow(1 - progress, 3);

            element.textContent = Math.round(
                target * eased
            ).toLocaleString();

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        }

        requestAnimationFrame(animate);
    });

    // Mobile sidebar.
    const sidebar = document.getElementById("sidebar");
    const menuToggle = document.getElementById("menuToggle");
    const overlay = document.getElementById("mobileOverlay");

    function closeMenu() {
        sidebar?.classList.remove("open");
        overlay?.classList.remove("show");
        menuToggle?.setAttribute("aria-expanded", "false");
    }

    menuToggle?.addEventListener("click", () => {
        const opened = sidebar.classList.toggle("open");

        overlay?.classList.toggle("show", opened);
        menuToggle.setAttribute("aria-expanded", String(opened));
    });

    overlay?.addEventListener("click", closeMenu);

    sidebar?.querySelectorAll("a").forEach(link => {
        link.addEventListener("click", closeMenu);
    });

    // Notification preview.
    const toast = document.getElementById("toast");
    const toastMessage = document.getElementById("toastMessage");
    let toastTimer;

    function showNotification(message) {
        if (!toast || !toastMessage) return;

        toastMessage.textContent = message;
        toast.classList.add("show");

        clearTimeout(toastTimer);

        toastTimer = setTimeout(() => {
            toast.classList.remove("show");
        }, 3500);
    }

    document.getElementById("notificationButton")
        ?.addEventListener("click", () => {
            showNotification(
                "No new notifications in this dashboard preview."
            );
        });

    document.getElementById("closeToast")
        ?.addEventListener("click", () => {
            toast?.classList.remove("show");
        });

    // Smooth scrolling for dashboard section links.
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener("click", event => {
            const selector = link.getAttribute("href");
            const target = document.querySelector(selector);

            if (!target) return;

            event.preventDefault();

            target.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        });
    });

});
