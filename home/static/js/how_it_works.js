
/* =========================================
   FUELFIX HOW IT WORKS - INTERACTIONS
========================================= */

"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const page = document.getElementById("how-page");

    if (!page) return;

    const reduceMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    /* Scroll reveal */
    const revealElements = page.querySelectorAll(".reveal");

    if (reduceMotion || !("IntersectionObserver" in window)) {
        revealElements.forEach(element => {
            element.classList.add("is-visible");
        });
    } else {
        const revealObserver = new IntersectionObserver(
            (entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        observer.unobserve(entry.target);
                    }
                });
            },
            {
                threshold: 0.12,
                rootMargin: "0px 0px -35px 0px"
            }
        );

        revealElements.forEach(element => {
            revealObserver.observe(element);
        });
    }

    /* Smooth scroll for links pointing to sections */
    page.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener("click", event => {
            const targetId = link.getAttribute("href");

            if (!targetId || targetId === "#") return;

            const target = page.querySelector(targetId);

            if (!target) return;

            event.preventDefault();

            target.scrollIntoView({
                behavior: reduceMotion ? "auto" : "smooth",
                block: "start"
            });
        });
    });

    /* Add subtle pointer movement to desktop illustration */
    const visual = page.querySelector(".hero-visual");

    if (visual && window.matchMedia("(hover: hover) and (pointer: fine)").matches
        && !reduceMotion) {

        visual.addEventListener("pointermove", event => {
            const rect = visual.getBoundingClientRect();

            const x = (event.clientX - rect.left) / rect.width - 0.5;
            const y = (event.clientY - rect.top) / rect.height - 0.5;

            visual.style.setProperty("--pointer-x", `${x * 8}px`);
            visual.style.setProperty("--pointer-y", `${y * 8}px`);
        });

        visual.addEventListener("pointerleave", () => {
            visual.style.setProperty("--pointer-x", "0px");
            visual.style.setProperty("--pointer-y", "0px");
        });
    }

    /* Optional: update the browser tab title */
    document.title = "FuelFix | How It Works";
});
