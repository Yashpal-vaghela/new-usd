document.addEventListener("DOMContentLoaded", function () {
    // -------------------------------------------------------------
    //smile_story_section
    // -------------------------------------------------------------
    var smileStorySwiper = new Swiper(".smile-story-swiper", {
        loop: true, 
        speed: 4000,
        slidesPerView: "auto", 
        spaceBetween: 30,
        autoplay: {
            delay: 0, 
            disableOnInteraction: false,
        },
        grabCursor: true,
        freeMode: {
            enabled: true,
            momentum: false,
        },
        allowTouchMove: true,
        breakpoints: {
            0: {
                spaceBetween: 10,
            },
            576: {
                spaceBetween: 20,
            },
            993: {
                spaceBetween: 30,
            },
        },
        on: {
            touchEnd: function (swiper) {
                setTimeout(function () {
                    if (swiper && swiper.autoplay) {
                        swiper.autoplay.start();
                    }
                }, 0);
            },
        },
    });
    // -------------------------------------------------------------    
    // smile_philosophy_section
    // -------------------------------------------------------------    
    if (typeof gsap !== "undefined") {
        const leftCol = document.querySelector(".smile_philosophy_reel_left_side");
        const rightCol = document.querySelector(
            ".smile_philosophy_reel_right_side",
        );

        function setupVerticalMarquee(col, direction) {
            if (!col) return;

            const items = Array.from(col.children);
            items.forEach((item) => {
                const clone = item.cloneNode(true);
                col.appendChild(clone);
            });

            const videos = col.querySelectorAll("video");
            videos.forEach((v) => {
                v.muted = true;
                v.play().catch((e) => console.log(e));
            });

            let tl = gsap.timeline({ repeat: -1 });

            function initAnimation() {
                tl.clear();
                gsap.set(col, { x: 0, y: 0 });

                const isMobile = window.innerWidth <= 995;

                if (isMobile) {
                    const originalWidth = col.scrollWidth / 2;
                    const duration = originalWidth / 50;

                    if (direction === -1) {
                        gsap.set(col, { x: 0 });
                        tl.to(col, {
                            x: -originalWidth,
                            duration: duration,
                            ease: "none",
                        });
                    } else {
                        gsap.set(col, { x: -originalWidth });
                        tl.to(col, {
                            x: 0,
                            duration: duration,
                            ease: "none",
                        });
                    }
                } else {
                    const originalHeight = col.scrollHeight / 2;
                    const duration = originalHeight / 50;

                    if (direction === -1) {
                        gsap.set(col, { y: 0 });
                        tl.to(col, {
                            y: -originalHeight,
                            duration: duration,
                            ease: "none",
                        });
                    } else {
                        gsap.set(col, { y: -originalHeight });
                        tl.to(col, {
                            y: 0,
                            duration: duration,
                            ease: "none",
                        });
                    }
                }
            }
            setTimeout(initAnimation, 100);
            window.addEventListener("resize", () => {
                setTimeout(initAnimation, 100);
            });
        }
        setupVerticalMarquee(leftCol, -1);
        setupVerticalMarquee(rightCol, 1);
    }
    // -------------------------------------------------------------
    // smile_solutions_section
    // -------------------------------------------------------------
    const swiper = new Swiper(".hmpswiper", {
        loop: true,
        centeredSlides: true,
        slidesPerView: 1,
        spaceBetween: 17,
        speed: 800,

        autoplay: {
            delay: 1200,
            disableOnInteraction: false,
            pauseOnMouseEnter: true,
        },

        grabCursor: true,
        observer: true,
        observeParents: true,

        pagination: {
            el: ".home-product-pagination",
            clickable: true,
        },

        breakpoints: {
            576: {
                slidesPerView: 1,
            },
            768: {
                slidesPerView: 2,
                spaceBetween: 30,
            },
            1024: {
                slidesPerView: 3,
                spaceBetween: 30,
            },
            1280: {
                slidesPerView: 3,
                spaceBetween: 50,
            },
        },

        on: {
            init: function () {
                this.update();
            },
        },
    });

    // -------------------------------------------------------------
    // smile_values_section
    // -------------------------------------------------------------
    if (typeof gsap !== "undefined" && typeof ScrollTrigger !== "undefined") {
        gsap.registerPlugin(ScrollTrigger);
        // ScrollTrigger.normalizeScroll(true);
        ScrollTrigger.config({ ignoreMobileResize: true });

        const cards = gsap.utils.toArray(".smile_values_card");

        if (cards.length > 0) {
            gsap.set(cards.slice(1), { y: () => window.innerHeight });

            const tl = gsap.timeline({
                scrollTrigger: {
                    trigger: ".smile_values_section_main",
                    start: "top 80px",
                    end: `+=${cards.length * 700}`,
                    pin: true,
                    anticipatePin: 1,
                    scrub: 1,
                },
            });

            cards.forEach((card, index) => {
                if (index === 0) return;
                tl.to(
                    card,
                    {
                        y: 0,
                        duration: 1,
                        ease: "none",
                    },
                    `stage${index}`,
                );

                for (let j = 0; j < index; j++) {
                    tl.to(
                        cards[j],
                        {
                            scale: 1 - 0.04 * (index - j),
                            y: `${-10 * (index - j)}px`,
                            duration: 1,
                            ease: "none",
                        },
                        `stage${index}`,
                    );
                }
            });
        }
    }
    
});
