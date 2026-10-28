"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const page = document.getElementById("services-page");

    if (!page) return;

    const reduceMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    // 1. Reveal elements as they enter the screen
    const revealElements = page.querySelectorAll(".reveal");

    if (
        reduceMotion ||
        !("IntersectionObserver" in window)
    ) {
        revealElements.forEach(element => {
            element.classList.add("is-visible");
        });
    } else {
        const observer = new IntersectionObserver(
            (entries, currentObserver) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        currentObserver.unobserve(entry.target);
                    }
                });
            },
            {
                threshold: 0.12,
                rootMargin: "0px 0px -30px 0px"
            }
        );

        revealElements.forEach(element => {
            observer.observe(element);
        });
    }

    // 2. Smooth scrolling for section links
    page.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener("click", event => {
            const targetId = link.getAttribute("href");

            if (!targetId || targetId === "#") return;

            const target = document.getElementById(
                targetId.substring(1)
            );

            if (!target || !page.contains(target)) return;

            event.preventDefault();

            target.scrollIntoView({
                behavior: reduceMotion ? "auto" : "smooth",
                block: "start"
            });
        });
    });

    // 3. Subtle mouse-follow effect on the hero car
    const visual = page.querySelector(".services-visual");

    if (
        visual &&
        !reduceMotion &&
        window.matchMedia(
            "(hover: hover) and (pointer: fine)"
        ).matches
    ) {
        visual.addEventListener("pointermove", event => {
            const rect = visual.getBoundingClientRect();

            const x = (event.clientX - rect.left) / rect.width - 0.5;
            const y = (event.clientY - rect.top) / rect.height - 0.5;

            visual.style.setProperty(
                "--mouse-x",
                `${x * 7}px`
            );

            visual.style.setProperty(
                "--mouse-y",
                `${y * 7}px`
            );
        });

        visual.addEventListener("pointerleave", () => {
            visual.style.setProperty("--mouse-x", "0px");
            visual.style.setProperty("--mouse-y", "0px");
        });
    }

    // 4. Interactive card tilt on desktop
    const cards = page.querySelectorAll(".service-card");

    if (
        !reduceMotion &&
        window.matchMedia(
            "(hover: hover) and (pointer: fine)"
        ).matches
    ) {
        cards.forEach(card => {
            card.addEventListener("pointermove", event => {
                const rect = card.getBoundingClientRect();

                const x = (event.clientX - rect.left) / rect.width;
                const y = (event.clientY - rect.top) / rect.height;

                const rotateY = (x - 0.5) * 4;
                const rotateX = (0.5 - y) * 4;

                card.style.transform =
                    `translateY(-8px) perspective(900px) ` +
                    `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
            });

            card.addEventListener("pointerleave", () => {
                card.style.transform = "";
            });
        });
    }

    // 5. Keep the browser tab title correct
    document.title = "FuelFix | Our Services";
});