document.addEventListener("DOMContentLoaded", function () {
    // -------------------------------------------------------------
    // smile_story_lightbox_popup
    // -------------------------------------------------------------
    const lightboxModal = document.getElementById("imageLightboxModal");
    const lightboxImg = document.getElementById("lightboxImg");
    const lightboxCloseBtn = document.getElementById("lightboxCloseBtn");
    const lightboxPrevBtn = document.getElementById("lightboxPrevBtn");
    const lightboxNextBtn = document.getElementById("lightboxNextBtn");
    const lightboxBackdrop = document.getElementById("lightboxBackdrop");
    const storySwiperEl = document.querySelector(".smile-story-swiper");

    let storyImages = [];

    function getImagesList() {
        if (!storySwiperEl) return [];
        const list = [];
        const seen = new Set();
        const imgs = storySwiperEl.querySelectorAll(".story-slide:not(.swiper-slide-duplicate) img");
        imgs.forEach((img, idx) => {
            if (img.src && !seen.has(img.src)) {
                seen.add(img.src);
                list.push({
                    src: img.src,
                    alt: img.alt || `Ultimate Smile Story ${idx + 1}`
                });
            }
        });
        return list;
    }

    let currentIndex = 0;

    function showImage(index) {
        storyImages = getImagesList();
        if (storyImages.length === 0 || !lightboxImg) return;
        currentIndex = (index + storyImages.length) % storyImages.length;
        lightboxImg.src = storyImages[currentIndex].src;
        lightboxImg.alt = storyImages[currentIndex].alt;
    }

    function pauseStorySwiper() {
        if (!window.smileStorySwiper) return;
        const swiper = window.smileStorySwiper;
        try {
            if (swiper.autoplay) {
                swiper.autoplay.stop();
            }
            const currentTranslate = typeof swiper.getTranslate === "function" ? swiper.getTranslate() : null;
            if (currentTranslate !== null && Number.isFinite(currentTranslate)) {
                swiper.setTransition(0);
                swiper.setTranslate(currentTranslate);
            }
            swiper.animating = false;
            if (swiper.onTranslateToWrapperTransitionEnd) {
                swiper.wrapperEl.removeEventListener("transitionend", swiper.onTranslateToWrapperTransitionEnd);
                swiper.onTranslateToWrapperTransitionEnd = null;
                delete swiper.onTranslateToWrapperTransitionEnd;
            }
        } catch (e) {
            console.error("pauseStorySwiper error:", e);
        }
    }

    function resumeStorySwiper() {
        if (!window.smileStorySwiper) return;
        const swiper = window.smileStorySwiper;
        try {
            swiper.animating = false;
            if (swiper.onTranslateToWrapperTransitionEnd) {
                swiper.wrapperEl.removeEventListener("transitionend", swiper.onTranslateToWrapperTransitionEnd);
                swiper.onTranslateToWrapperTransitionEnd = null;
                delete swiper.onTranslateToWrapperTransitionEnd;
            }
            if (swiper.params.loop && typeof swiper.loopFix === "function") {
                swiper.loopFix();
            }
            if (typeof swiper.updateActiveIndex === "function") {
                swiper.updateActiveIndex();
            }
            if (swiper.autoplay) {
                swiper.autoplay.start();
            }
            requestAnimationFrame(() => {
                if (swiper && !swiper.animating && typeof swiper.slideNext === "function") {
                    swiper.slideNext(swiper.params.speed, true, true);
                }
            });
        } catch (e) {
            console.error("resumeStorySwiper error:", e);
        }
    }

    function openLightbox(index) {
        if (!lightboxModal || !lightboxImg) return;
        storyImages = getImagesList();
        if (storyImages.length === 0) return;

        showImage(index);
        lightboxModal.classList.add("active");
        lightboxModal.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";

        pauseStorySwiper();
    }

    function closeLightbox() {
        if (!lightboxModal) return;
        lightboxModal.classList.remove("active");
        lightboxModal.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";

        setTimeout(() => {
            if (!lightboxModal.classList.contains("active") && lightboxImg) {
                lightboxImg.src = "";
            }
        }, 300);

        resumeStorySwiper();
    }

    function prevImage() {
        if (lightboxModal && lightboxModal.classList.contains("active")) {
            showImage(currentIndex - 1);
        }
    }

    function nextImage() {
        if (lightboxModal && lightboxModal.classList.contains("active")) {
            showImage(currentIndex + 1);
        }
    }

    window.openStoryLightbox = function (imgSrc) {
        storyImages = getImagesList();
        if (!storyImages || storyImages.length === 0) return;
        let targetIdx = storyImages.findIndex((item) => {
            if (!item.src || !imgSrc) return false;
            return item.src === imgSrc || item.src.endsWith(imgSrc) || imgSrc.endsWith(item.src);
        });
        if (targetIdx === -1) targetIdx = 0;
        openLightbox(targetIdx);
    };

    // -------------------------------------------------------------
    //smile_story_section
    // -------------------------------------------------------------
    window.smileStorySwiper = new Swiper(".smile-story-swiper", {
        loop: true, 
        speed: 4000,
        slidesPerView: "auto", 
        spaceBetween: 30,
        autoplay: {
            delay: 0, 
            disableOnInteraction: false,
        },
        preventClicks: false,
        preventClicksPropagation: false,
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
            click: function (swiper, event) {
                const slide = swiper.clickedSlide || (event && event.target ? event.target.closest(".story-slide") : null);
                if (!slide) return;
                const img = slide.querySelector("img");
                if (!img) return;

                storyImages = getImagesList();
                let targetIdx = storyImages.findIndex((item) => item.src === img.src);
                if (targetIdx === -1) targetIdx = 0;
                openLightbox(targetIdx);
            },
            touchEnd: function (swiper) {
                setTimeout(function () {
                    if (lightboxModal && lightboxModal.classList.contains("active")) {
                        return; // Keep paused while lightbox popup is open
                    }
                    if (swiper && swiper.autoplay && !swiper.autoplay.running) {
                        resumeStorySwiper();
                    }
                }, 100);
            },
        },
    });

    if (lightboxModal) {
        if (lightboxCloseBtn) lightboxCloseBtn.addEventListener("click", closeLightbox);
        if (lightboxBackdrop) lightboxBackdrop.addEventListener("click", closeLightbox);
        if (lightboxPrevBtn) {
            lightboxPrevBtn.addEventListener("click", function (e) {
                e.stopPropagation();
                prevImage();
            });
        }
        if (lightboxNextBtn) {
            lightboxNextBtn.addEventListener("click", function (e) {
                e.stopPropagation();
                nextImage();
            });
        }

        lightboxModal.addEventListener("click", function (e) {
            if (e.target === lightboxModal) {
                closeLightbox();
            }
        });

        // Keyboard navigation: ArrowLeft (prev), ArrowRight (next), Escape (close)
        document.addEventListener("keydown", function (e) {
            if (!lightboxModal || !lightboxModal.classList.contains("active")) return;

            if (e.key === "ArrowLeft") {
                e.preventDefault();
                prevImage();
            } else if (e.key === "ArrowRight") {
                e.preventDefault();
                nextImage();
            } else if (e.key === "Escape") {
                e.preventDefault();
                closeLightbox();
            }
        });

        // Touch swipe gestures for mobile
        let touchStartX = 0;
        let touchStartY = 0;
        let touchEndX = 0;
        let touchEndY = 0;

        lightboxModal.addEventListener(
            "touchstart",
            function (e) {
                touchStartX = e.changedTouches[0].screenX;
                touchStartY = e.changedTouches[0].screenY;
            },
            { passive: true }
        );

        lightboxModal.addEventListener(
            "touchend",
            function (e) {
                touchEndX = e.changedTouches[0].screenX;
                touchEndY = e.changedTouches[0].screenY;
                const diffX = touchEndX - touchStartX;
                const diffY = touchEndY - touchStartY;
                const minSwipeDistance = 40;

                if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > minSwipeDistance) {
                    if (diffX < 0) {
                        nextImage();
                    } else {
                        prevImage();
                    }
                }
            },
            { passive: true }
        );
    }

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
    if (document.querySelector(".smile-solutions-swiper")) {
        var smileSolutionsSwiper = new Swiper(".smile-solutions-swiper", {
            slidesPerView: 1,
            spaceBetween: 22,
            loop: true,
            speed: 800,
            grabCursor: true,
            allowTouchMove: true,
            autoplay: {
                delay: 2500,
                disableOnInteraction: false,
                pauseOnMouseEnter: true,
            },
            pagination: {
                el: ".smile-solutions-pagination",
                clickable: true,
            },
            breakpoints: {
                576: {
                    slidesPerView: 1.5,
                    spaceBetween: 20,
                },
                768: {
                    slidesPerView: 2,
                    spaceBetween: 22,
                },
                1024: {
                    slidesPerView: 2.5,
                    spaceBetween: 22,
                },
                1200: {
                    slidesPerView: 3,
                    spaceBetween: 22,
                },
            },
        });
    }
  
    // -------------------------------------------------------------
    // about_page_contact_form (Country Code Flag + ContactHomePage + SweetAlert)
    // -------------------------------------------------------------
    const aboutContactForm = document.getElementById("aboutContactForm");
    const countrySelectBtn = document.getElementById("countrySelectBtn");
    const countryDropdown = document.getElementById("countryDropdown");
    const countrySearchInput = document.getElementById("countrySearchInput");
    const countryListEl = document.getElementById("countryList");
    const selectedFlag = document.getElementById("selectedFlag");
    const selectedCode = document.getElementById("selectedCode");
    const phoneInput = document.getElementById("phoneInput");
    const realPhoneInput = document.getElementById("realPhoneInput");
    const fullPhoneInput = document.getElementById("fullPhoneInput");
    const pincodeInput = document.getElementById("pincodeInput");
    const cityInput = document.getElementById("cityInput");
    const aboutFormSubmitBtn = document.getElementById("aboutFormSubmitBtn");

    if (aboutContactForm && countrySelectBtn && phoneInput) {
        const defaultCountries = [
            { name: "India", code: "IN", dialCode: "+91" },
            { name: "United States", code: "US", dialCode: "+1" },
            { name: "United Kingdom", code: "GB", dialCode: "+44" },
            { name: "United Arab Emirates", code: "AE", dialCode: "+971" },
            { name: "Canada", code: "CA", dialCode: "+1" },
            { name: "Australia", code: "AU", dialCode: "+61" },
            { name: "Saudi Arabia", code: "SA", dialCode: "+966" },
            { name: "Germany", code: "DE", dialCode: "+49" },
            { name: "France", code: "FR", dialCode: "+33" },
            { name: "Singapore", code: "SG", dialCode: "+65" },
            { name: "Oman", code: "OM", dialCode: "+968" },
            { name: "Qatar", code: "QA", dialCode: "+974" },
            { name: "Kuwait", code: "KW", dialCode: "+965" },
            { name: "Bahrain", code: "BH", dialCode: "+973" },
            { name: "Nepal", code: "NP", dialCode: "+977" },
            { name: "Bangladesh", code: "BD", dialCode: "+880" },
            { name: "Pakistan", code: "PK", dialCode: "+92" },
            { name: "Sri Lanka", code: "LK", dialCode: "+94" },
            { name: "Malaysia", code: "MY", dialCode: "+60" },
            { name: "Indonesia", code: "ID", dialCode: "+62" },
            { name: "Thailand", code: "TH", dialCode: "+66" },
            { name: "Italy", code: "IT", dialCode: "+39" },
            { name: "Spain", code: "ES", dialCode: "+34" },
            { name: "Netherlands", code: "NL", dialCode: "+31" },
            { name: "Switzerland", code: "CH", dialCode: "+41" },
            { name: "South Africa", code: "ZA", dialCode: "+27" },
            { name: "New Zealand", code: "NZ", dialCode: "+64" }
        ];

        let countriesList = [...defaultCountries];
        let currentSelected = { name: "India", code: "IN", dialCode: "+91" };

        function getFlagUrl(code) {
            return `https://flagcdn.com/w40/${code.toLowerCase()}.png`;
        }

        function renderCountryList(list) {
            if (!countryListEl) return;
            countryListEl.innerHTML = "";
            if (list.length === 0) {
                countryListEl.innerHTML = `<li class="no-country-found">No country found</li>`;
                return;
            }

            list.forEach((country) => {
                const li = document.createElement("li");
                li.className = `country-item ${country.code === currentSelected.code ? "active" : ""}`;
                li.dataset.code = country.code;
                li.dataset.dialCode = country.dialCode;
                li.dataset.name = country.name;

                li.innerHTML = `
                    <div class="country-item-info">
                        <img src="${getFlagUrl(country.code)}" alt="${country.code}" class="country-flag-img" loading="lazy" />
                        <span class="country-item-name">${country.name}</span>
                    </div>
                    <span class="country-item-code">${country.dialCode}</span>
                `;

                li.addEventListener("click", function (e) {
                    e.stopPropagation();
                    selectCountry(country);
                    closeCountryDropdown();
                });

                countryListEl.appendChild(li);
            });
        }

        function selectCountry(country) {
            currentSelected = country;
            if (selectedFlag) {
                selectedFlag.src = getFlagUrl(country.code);
                selectedFlag.alt = country.code;
            }
            if (selectedCode) {
                selectedCode.textContent = country.dialCode;
            }

            if (countryListEl) {
                countryListEl.querySelectorAll(".country-item").forEach((el) => {
                    if (el.dataset.code === country.code) {
                        el.classList.add("active");
                    } else {
                        el.classList.remove("active");
                    }
                });
            }

            updateFullPhone();
        }

        function updateFullPhone() {
            if (!phoneInput) return;
            const number = phoneInput.value.trim();
            const formatted = number ? `${currentSelected.dialCode} ${number}` : "";
            if (fullPhoneInput) fullPhoneInput.value = formatted;
            if (realPhoneInput) realPhoneInput.value = formatted;
        }

        function openCountryDropdown() {
            if (!countryDropdown) return;
            countryDropdown.classList.add("show");
            countrySelectBtn.classList.add("active");
            countrySelectBtn.setAttribute("aria-expanded", "true");
            if (countrySearchInput) {
                countrySearchInput.value = "";
                renderCountryList(countriesList);
                setTimeout(() => countrySearchInput.focus(), 60);
            }
        }

        function closeCountryDropdown() {
            if (!countryDropdown) return;
            countryDropdown.classList.remove("show");
            countrySelectBtn.classList.remove("active");
            countrySelectBtn.setAttribute("aria-expanded", "false");
        }

        function toggleCountryDropdown() {
            if (countryDropdown && countryDropdown.classList.contains("show")) {
                closeCountryDropdown();
            } else {
                openCountryDropdown();
            }
        }

        countrySelectBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            toggleCountryDropdown();
        });

        if (countrySearchInput) {
            countrySearchInput.addEventListener("input", function (e) {
                const query = e.target.value.toLowerCase().trim();
                const filtered = countriesList.filter((c) =>
                    c.name.toLowerCase().includes(query) || c.dialCode.includes(query) || c.code.toLowerCase().includes(query)
                );
                renderCountryList(filtered);
            });

            countrySearchInput.addEventListener("click", function (e) {
                e.stopPropagation();
            });
        }

        phoneInput.addEventListener("input", updateFullPhone);

        document.addEventListener("click", function (e) {
            if (countryDropdown && !countryDropdown.contains(e.target) && !countrySelectBtn.contains(e.target)) {
                closeCountryDropdown();
            }
        });

        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && countryDropdown && countryDropdown.classList.contains("show")) {
                closeCountryDropdown();
            }
        });

        // Initialize country list
        renderCountryList(countriesList);
        updateFullPhone();

        // Optionally fetch extended country list from REST countries if available
        if (typeof fetchCountryList === "function") {
            try {
                fetchCountryList(function (apiList) {
                    if (apiList && apiList.length > 0) {
                        countriesList = apiList;
                        renderCountryList(countriesList);
                    }
                });
            } catch (err) {
                // Non-blocking
            }
        }

        // Pincode auto-lookup for city if country_utils.js is loaded
        const pincodeSpinner = document.getElementById("pincodeSpinner");
        const pincodeStatusIcon = document.getElementById("pincodeStatusIcon");

        function setPincodeStatus(state) {
            if (state === "loading") {
                if (pincodeSpinner) pincodeSpinner.style.display = "block";
                if (pincodeStatusIcon) {
                    pincodeStatusIcon.style.display = "none";
                    pincodeStatusIcon.innerHTML = "";
                }
            } else if (state === "valid") {
                if (pincodeSpinner) pincodeSpinner.style.display = "none";
                if (pincodeStatusIcon) {
                    pincodeStatusIcon.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
                    pincodeStatusIcon.style.display = "flex";
                }
            } else if (state === "invalid") {
                if (pincodeSpinner) pincodeSpinner.style.display = "none";
                if (pincodeStatusIcon) {
                    pincodeStatusIcon.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;
                    pincodeStatusIcon.style.display = "flex";
                }
            } else {
                if (pincodeSpinner) pincodeSpinner.style.display = "none";
                if (pincodeStatusIcon) {
                    pincodeStatusIcon.style.display = "none";
                    pincodeStatusIcon.innerHTML = "";
                }
            }
        }

        if (pincodeInput && cityInput && typeof lookupPincode === "function") {
            // City input is readonly by default until pincode is evaluated
            cityInput.readOnly = true;

            let pinTimer = null;
            let lastFetchedPin = "";

            function handlePincodeInput(immediate = false) {
                clearTimeout(pinTimer);
                const pin = pincodeInput.value.trim();

                // If pincode is completely removed or empty, remove city, lock it to readOnly, and reset to idle
                if (!pin) {
                    cityInput.value = "";
                    cityInput.readOnly = true;
                    lastFetchedPin = "";
                    setPincodeStatus("idle");
                    return;
                }

                // Real-time loader: show golden spinner immediately on input change
                setPincodeStatus("loading");

                const isIndia = (currentSelected.code || "IN").toUpperCase() === "IN";
                const digits = pin.replace(/\D/g, "");

                const doValidate = async () => {
                    const currentPin = pincodeInput.value.trim();
                    if (!currentPin) {
                        cityInput.value = "";
                        cityInput.readOnly = true;
                        lastFetchedPin = "";
                        setPincodeStatus("idle");
                        return;
                    }

                    // For India, PIN must be exactly 6 digits. If not, it is invalid (allow user to manually add city)
                    if (isIndia && digits.length !== 6) {
                        if (cityInput.readOnly) {
                            cityInput.value = "";
                        }
                        cityInput.readOnly = false;
                        lastFetchedPin = currentPin;
                        setPincodeStatus("invalid");
                        return;
                    }

                    // For non-India, minimum 3 characters
                    if (!isIndia && currentPin.length < 3) {
                        if (cityInput.readOnly) {
                            cityInput.value = "";
                        }
                        cityInput.readOnly = false;
                        lastFetchedPin = currentPin;
                        setPincodeStatus("invalid");
                        return;
                    }

                    try {
                        const searchPin = isIndia ? digits : currentPin;
                        const res = await lookupPincode(searchPin, currentSelected.code, currentSelected.name);

                        // If user changed input while fetching, avoid stale update
                        if (pincodeInput.value.trim() !== currentPin) {
                            return;
                        }

                        if (res && res.valid && res.city) {
                            cityInput.value = res.city;
                            cityInput.readOnly = true; // Auto-fetched city cannot be manually edited
                            lastFetchedPin = currentPin;
                            setPincodeStatus("valid");
                        } else {
                            // Invalid pincode or no city found: allow user to manually add city
                            if (cityInput.readOnly) {
                                cityInput.value = "";
                            }
                            cityInput.readOnly = false;
                            lastFetchedPin = currentPin;
                            setPincodeStatus("invalid");
                        }
                    } catch (err) {
                        if (pincodeInput.value.trim() === currentPin) {
                            if (cityInput.readOnly) {
                                cityInput.value = "";
                            }
                            cityInput.readOnly = false;
                            lastFetchedPin = currentPin;
                            setPincodeStatus("invalid");
                        }
                    }
                };

                if (immediate) {
                    doValidate();
                } else {
                    pinTimer = setTimeout(doValidate, 350);
                }
            }

            pincodeInput.addEventListener("input", () => handlePincodeInput(false));
            pincodeInput.addEventListener("change", () => handlePincodeInput(true));
            pincodeInput.addEventListener("blur", () => {
                if (pincodeInput.value.trim()) {
                    handlePincodeInput(true);
                }
            });
        }

        // Handle AJAX Form Submission with SweetAlert
        aboutContactForm.addEventListener("submit", async function (e) {
            e.preventDefault();

            // Validate phone
            const rawPhone = (phoneInput.value || "").trim();
            if (!rawPhone) {
                if (typeof Swal !== "undefined") {
                    Swal.fire({
                        icon: "warning",
                        title: "Phone Required",
                        text: "Please enter your phone number.",
                        confirmButtonColor: "#C3942F"
                    });
                } else {
                    alert("Please enter your phone number.");
                }
                phoneInput.focus();
                return;
            }

            // Sync phone fields
            updateFullPhone();

            // Check reCAPTCHA if present
            const recaptchaWidget = aboutContactForm.querySelector(".g-recaptcha");
            if (recaptchaWidget) {
                let captchaResponse = "";
                const textarea = aboutContactForm.querySelector('textarea[name="g-recaptcha-response"]');
                if (textarea && textarea.value.trim() !== "") {
                    captchaResponse = textarea.value.trim();
                } else if (typeof grecaptcha !== "undefined" && grecaptcha.getResponse) {
                    try {
                        captchaResponse = grecaptcha.getResponse();
                    } catch (err) {
                        captchaResponse = "";
                    }
                }

                if (!captchaResponse) {
                    if (typeof Swal !== "undefined") {
                        Swal.fire({
                            icon: "warning",
                            title: "Verification Required",
                            text: "Please check the CAPTCHA box before submitting.",
                            confirmButtonColor: "#C3942F"
                        });
                    } else {
                        alert("Please check the CAPTCHA box before submitting.");
                    }
                    return;
                }
            }

            // Loading state on button
            const submitBtn = aboutFormSubmitBtn || aboutContactForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn ? submitBtn.innerHTML : "Send Message";
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Sending...';
            }

            try {
                const formData = new FormData(aboutContactForm);
                const actionUrl = aboutContactForm.action || window.location.href;

                const response = await fetch(actionUrl, {
                    method: "POST",
                    body: formData,
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });

                const data = await response.json();

                if (response.ok && data.status === "success") {
                    if (typeof Swal !== "undefined") {
                        Swal.fire({
                            icon: "success",
                            title: "Thank You!",
                            text: data.message || "Your message has been submitted successfully.",
                            confirmButtonColor: "#C3942F",
                            timer: 3500
                        });
                    } else {
                        alert(data.message || "Your message has been submitted successfully.");
                    }

                    aboutContactForm.reset();
                    cityInput.readOnly = true;
                    setPincodeStatus("idle");
                    selectCountry({ name: "India", code: "IN", dialCode: "+91" });

                    if (typeof grecaptcha !== "undefined" && grecaptcha.reset) {
                        try {
                            grecaptcha.reset();
                        } catch (err) {}
                    }
                } else {
                    const errorMsg = (data && data.message) ? data.message : "Something went wrong! Please check your details.";
                    if (typeof Swal !== "undefined") {
                        Swal.fire({
                            icon: "error",
                            title: "Submission Error",
                            text: errorMsg,
                            confirmButtonColor: "#C3942F"
                        });
                    } else {
                        alert(errorMsg);
                    }
                }
            } catch (err) {
                console.error("Form submit error:", err);
                if (typeof Swal !== "undefined") {
                    Swal.fire({
                        icon: "error",
                        title: "Network Error",
                        text: "Unable to connect to the server. Please try again later.",
                        confirmButtonColor: "#C3942F"
                    });
                } else {
                    alert("Unable to connect to the server. Please try again later.");
                }
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                }
            }
        });
    }
  
});
