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
    const nameInput = document.getElementById("nameInput");
    const emailInput = document.getElementById("emailInput");
    const phoneInput = document.getElementById("phoneInput");
    const realPhoneInput = document.getElementById("realPhoneInput");
    const fullPhoneInput = document.getElementById("fullPhoneInput");
    const phoneFieldBox = document.getElementById("phoneFieldBox");
    const phoneStatusIcon = document.getElementById("phoneStatusIcon");
    const phoneStatusBadge = document.getElementById("phoneStatusBadge");
    const phoneFeedback = document.getElementById("phoneFeedback");

    const pincodeInput = document.getElementById("pincodeInput");
    const pincodeFieldBox = document.getElementById("pincodeFieldBox");
    const cityInput = document.getElementById("cityInput");
    const messageInput = document.getElementById("messageInput");
    const pincodeSpinner = document.getElementById("pincodeSpinner");
    const pincodeStatusIcon = document.getElementById("pincodeStatusIcon");
    const pincodeStatusBadge = document.getElementById("pincodeStatusBadge");
    const pincodeFeedback = document.getElementById("pincodeFeedback");
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

        /* PHONE REAL-TIME VALIDATION via country_utils.js */
        let phoneCtrl = null;
        if (typeof attachPhoneValidation === "function") {
            phoneCtrl = attachPhoneValidation({
                phoneInput: phoneInput,
                fullPhoneInput: fullPhoneInput,
                getCountry: () => currentSelected,
                fieldBox: phoneFieldBox,
                statusIcon: phoneStatusIcon,
                statusBadge: phoneStatusBadge,
                feedback: phoneFeedback
            });
        }

        /* PINCODE REAL-TIME VALIDATION & AUTO-FETCH via country_utils.js */
        let pincodeCtrl = null;
        if (typeof attachPincodeAutofill === "function") {
            pincodeCtrl = attachPincodeAutofill({
                pincodeInput: pincodeInput,
                cityInput: cityInput,
                getCountry: () => currentSelected,
                fieldBox: pincodeFieldBox,
                spinner: pincodeSpinner,
                statusIcon: pincodeStatusIcon,
                statusBadge: pincodeStatusBadge,
                feedback: pincodeFeedback,
                pulseClass: 'city-highlight-pulse'
            });
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

            // Dynamically update phone validation rules & limits
            if (phoneCtrl) {
                phoneCtrl.updateCountry(currentSelected);
            } else {
                updateFullPhone();
            }

            // Dynamically update pincode validation rules & limits
            if (pincodeCtrl) {
                pincodeCtrl.updateCountry(currentSelected); 
            }
        }

        function updateFullPhone() {
            if (phoneCtrl) {
                phoneCtrl.updateFullPhone();
            } else {
                if (!phoneInput) return;
                const number = phoneInput.value.trim();
                const formatted = number ? `${currentSelected.dialCode} ${number}` : "";
                if (fullPhoneInput) fullPhoneInput.value = formatted;
            }
            if (realPhoneInput && fullPhoneInput) {
                realPhoneInput.value = fullPhoneInput.value;
            }
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
        selectCountry(currentSelected);

        // Fetch extended country list from REST countries API
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

        // Handle AJAX Form Submission with SweetAlert & strict country-based validations
        aboutContactForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            updateFullPhone();

            // 1. Validate Full Name
            if (nameInput && !nameInput.value.trim()) {
                if (typeof Swal !== "undefined") {
                    Swal.fire({
                        icon: "warning",
                        title: "Name Required",
                        text: "Please enter your full name.",
                        confirmButtonColor: "#C3942F"
                    });
                } else {
                    alert("Please enter your full name.");
                }
                nameInput.focus();
                return;
            }

            // 2. Validate Email
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (emailInput && (!emailInput.value.trim() || !emailRegex.test(emailInput.value.trim()))) {
                if (typeof Swal !== "undefined") {
                    Swal.fire({
                        icon: "warning",
                        title: "Invalid Email",
                        text: "Please enter a valid email address.",
                        confirmButtonColor: "#C3942F"
                    });
                } else {
                    alert("Please enter a valid email address.");
                }
                emailInput.focus();
                return;
            }

            // 3. Country-Based Phone Validation
            if (phoneCtrl) {
                const phoneValid = phoneCtrl.validate(true);
                if (!phoneValid) {
                    phoneInput.focus();
                    return;
                }
            } else {
                const rawPhone = (phoneInput.value || "").trim();
                if (!rawPhone) {
                    phoneInput.focus();
                    return;
                }
            }

            // 4. Country-Based Pincode Validation
            const pinVal = (pincodeInput.value || "").trim();
            if (typeof validatePostalCode === "function") {
                const pinRes = validatePostalCode(pinVal, currentSelected.code, currentSelected.name);
                if (!pinRes.valid) {
                    if (pincodeCtrl) {
                        pincodeCtrl.setStatus('invalid', pinRes.message, pinRes.badge);
                    }
                    pincodeInput.focus();
                    return;
                }
            }

            // 5. Validate City
            if (cityInput && !cityInput.value.trim()) {
                if (typeof Swal !== "undefined") {
                    Swal.fire({
                        icon: "warning",
                        title: "City Required",
                        text: "Please enter your city name or enter a valid PIN code to auto-locate.",
                        confirmButtonColor: "#C3942F"
                    });
                } else {
                    alert("Please enter your city name.");
                }
                cityInput.focus();
                return;
            }

            // 6. Validate Message
            if (messageInput && !messageInput.value.trim()) {
                if (typeof Swal !== "undefined") {
                    Swal.fire({
                        icon: "warning",
                        title: "Message Required",
                        text: "Please enter your message.",
                        confirmButtonColor: "#C3942F"
                    });
                } else {
                    alert("Please enter your message.");
                }
                messageInput.focus();
                return;
            }

            // 7. Check reCAPTCHA if present
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
                    if (phoneCtrl) phoneCtrl.reset();
                    if (pincodeCtrl) pincodeCtrl.reset();
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
  
    // -------------------------------------------------------------
    // Responsive AOS for Smile Values Cards (fade-up on <= 576px)
    // -------------------------------------------------------------
    function updateSmileValuesAos() {
        const isMobile = window.innerWidth <= 576;
        const cards = document.querySelectorAll(".smile_values_cards_main .smile_values_card_main");
        cards.forEach((card) => {
            if (!card.dataset.aosDesktop) {
                card.dataset.aosDesktop = card.getAttribute("data-aos") || "fade-up";
            }
            const desiredAos = isMobile ? "fade-up" : card.dataset.aosDesktop;
            if (card.getAttribute("data-aos") !== desiredAos) {
                card.setAttribute("data-aos", desiredAos);
            }
        });
    }

    updateSmileValuesAos();

    window.addEventListener("resize", function () {
        updateSmileValuesAos();
        if (typeof AOS !== "undefined" && typeof AOS.refresh === "function") {
            AOS.refresh();
        }
    });

});
