/**
 * Shared utility functions for Country & Pincode/Postal Code lookups
 * Used across lead forms, contact pages, and appointment modals.
 */

/**
 * 1. Fetch and format global country list from REST Countries API
 * @param {Function} callback Callback receiving sorted apiList with India ('IN') at the top
 */
function fetchCountryList(callback) {
    fetch("https://restcountries.com/v3.1/all?fields=name,cca2,idd,flags")
        .then((res) => {
            if (!res.ok) throw new Error("API response error");
            return res.json();
        })
        .then((data) => {
            const apiList = [];
            data.forEach((item) => {
                if (item.idd && item.idd.root) {
                    const root = item.idd.root;
                    let suffix = "";
                    if (item.idd.suffixes && item.idd.suffixes.length === 1) {
                        suffix = item.idd.suffixes[0];
                    }
                    const dialCode = root + suffix;
                    if (dialCode && item.cca2 && item.name && item.name.common) {
                        apiList.push({
                            name: item.name.common,
                            code: item.cca2.toUpperCase(),
                            dialCode: dialCode,
                        });
                    }
                }
            });

            if (apiList.length > 0) {
                apiList.sort((a, b) => a.name.localeCompare(b.name));
                const inIdx = apiList.findIndex((c) => c.code === "IN");
                if (inIdx > -1) {
                    const indiaObj = apiList.splice(inIdx, 1)[0];
                    apiList.unshift(indiaObj);
                }
                if (typeof callback === "function") {
                    callback(apiList);
                }
            }
        })
        .catch((err) => {
            console.log("Using built-in country database", err);
        });
}

/**
 * 2. Shared Pincode Cache and Abort Controller
 */
const _pincodeCache = {};
let _pincodeAbortCtrl = null;

/**
 * Shared Pincode / Postal Code lookup function
 * Supports:
 * - India Post API (with automatic digit extraction)
 * - International postal codes via Zippopotam
 * - Nominatim OpenStreetMap fallback
 * 
 * @param {string} pinValue Raw postal/pincode string
 * @param {string} countryCode 2-letter ISO country code (e.g. 'IN', 'US')
 * @param {string} countryName Country name (e.g. 'India', 'United States')
 * @returns {Promise<{valid: boolean, city?: string, state?: string, message?: string, badge?: string}|null>}
 */
async function lookupPincode(pinValue, countryCode = 'IN', countryName = 'India') {
    const rawPin = (pinValue || '').trim();
    if (!rawPin) {
        return { valid: false, empty: true };
    }

    const cacheKey = `${countryCode}_${rawPin.toUpperCase()}`;
    if (_pincodeCache[cacheKey]) {
        return _pincodeCache[cacheKey];
    }

    if (_pincodeAbortCtrl) {
        _pincodeAbortCtrl.abort();
    }
    _pincodeAbortCtrl = new AbortController();
    const signal = _pincodeAbortCtrl.signal;

    // Fallback via Nominatim (OpenStreetMap)
    async function fallbackNominatim() {
        try {
            const url = `https://nominatim.openstreetmap.org/search?postalcode=${encodeURIComponent(rawPin)}&countrycodes=${countryCode.toLowerCase()}&format=json&addressdetails=1`;
            const res = await fetch(url, { signal });
            if (!res.ok) throw new Error('Network error');
            const data = await res.json();
            if (data && data.length > 0) {
                const addr = data[0].address || {};
                const city = addr.city || addr.town || addr.village || addr.municipality || addr.county || addr.suburb || addr.state || data[0].name || '';
                const state = addr.state || '';
                const result = {
                    valid: !!city,
                    city: city,
                    state: state,
                    message: city ? `✓ Located: ${city}${state ? ', ' + state : ''} (${countryName})` : `Invalid postal code for ${countryName}`,
                    badge: city ? 'Valid Code' : 'Invalid'
                };
                _pincodeCache[cacheKey] = result;
                return result;
            }
            const invalidRes = {
                valid: false,
                message: `Invalid postal code for ${countryName}`,
                badge: 'Invalid'
            };
            _pincodeCache[cacheKey] = invalidRes;
            return invalidRes;
        } catch (err) {
            if (err.name === 'AbortError') return null;
            return {
                valid: false,
                message: `Unable to verify postal code for ${countryName}`,
                badge: 'Invalid'
            };
        }
    }

    // 1. India specific postal lookup
    if (countryCode === 'IN') {
        const cleanPin = rawPin.replace(/\D/g, '');
        if (cleanPin.length !== 6) {
            return {
                valid: false,
                message: 'Please enter a 6-digit Indian PIN code (e.g. 365601)',
                badge: 'Invalid PIN'
            };
        }

        try {
            const res = await fetch(`https://api.postalpincode.in/pincode/${cleanPin}`, { signal });
            const data = await res.json();
            if (data && data[0] && data[0].Status === 'Success' && data[0].PostOffice && data[0].PostOffice.length > 0) {
                const po = data[0].PostOffice[0];
                const city = po.District || po.Block || po.Taluk || po.Circle || po.Name || '';
                const state = po.State || '';
                const result = {
                    valid: true,
                    city: city,
                    state: state,
                    message: `✓ Located: ${city}${state ? ', ' + state : ''}`,
                    badge: 'Valid PIN'
                };
                _pincodeCache[cacheKey] = result;
                return result;
            } else {
                const result = {
                    valid: false,
                    message: 'PIN code not found in India Post database',
                    badge: 'Invalid PIN'
                };
                _pincodeCache[cacheKey] = result;
                return result;
            }
        } catch (err) {
            if (err.name === 'AbortError') return null;
            return await fallbackNominatim();
        }
    }

    // 2. International (Zippopotam)
    try {
        const cleanPin = encodeURIComponent(rawPin.replace(/\s+/g, ''));
        const res = await fetch(`https://api.zippopotam.us/${countryCode.toLowerCase()}/${cleanPin}`, { signal });
        if (res.ok) {
            const data = await res.json();
            if (data && data.places && data.places.length > 0) {
                const place = data.places[0];
                const city = place['place name'] || '';
                const state = place['state'] || place['state abbreviation'] || '';
                const result = {
                    valid: true,
                    city: city,
                    state: state,
                    message: `✓ Located: ${city}${state ? ', ' + state : ''} (${countryName})`,
                    badge: 'Valid Code'
                };
                _pincodeCache[cacheKey] = result;
                return result;
            }
        }
        return await fallbackNominatim();
    } catch (err) {
        if (err.name === 'AbortError') return null;
        return await fallbackNominatim();
    }
}

/**
 * 3. Centralized Pincode UI Attachment Helper
 * Handles debouncing, visual status indicators (spinner, icon, badge, feedback),
 * dynamic city input locking/unlocking, pulse animations, placeholder updates,
 * and form submission guards.
 *
 * @param {Object} options Configuration object
 * @param {HTMLInputElement|string} options.pincodeInput Pincode input element or selector
 * @param {HTMLInputElement|string} options.cityInput City input element or selector
 * @param {Function|Object} options.getCountry Function returning { code: 'IN', name: 'India' } or static country object
 * @param {HTMLElement|string} [options.spinner] Spinner element or selector
 * @param {HTMLElement|string} [options.statusIcon] Status icon element or selector
 * @param {HTMLElement|string} [options.statusBadge] Status badge element or selector
 * @param {HTMLElement|string} [options.feedback] Feedback text element or selector
 * @param {HTMLFormElement|string} [options.form] Form element or selector to guard against empty city
 * @param {string} [options.pulseClass='city-highlight-pulse'] CSS animation class to pulse on city input
 * @param {Function} [options.onValid] Optional callback when valid pincode and city are found
 * @param {Function} [options.onInvalid] Optional callback when pincode is invalid
 * @returns {Object} Controller with { triggerLookup, updatePlaceholder, setStatus, reset }
 */
function attachPincodeAutofill(options) {
    function resolve(el) {
        if (!el) return null;
        if (typeof el === 'string') return document.querySelector(el);
        return el;
    }

    const pinEl = resolve(options.pincodeInput);
    const cityEl = resolve(options.cityInput);
    const spinnerEl = resolve(options.spinner);
    const iconEl = resolve(options.statusIcon);
    const badgeEl = resolve(options.statusBadge);
    const feedbackEl = resolve(options.feedback);
    const formEl = resolve(options.form);
    const pulseClass = options.pulseClass || 'city-highlight-pulse';

    let debounceTimer = null;

    function getCountryObj() {
        if (typeof options.getCountry === 'function') {
            return options.getCountry() || { code: 'IN', name: 'India' };
        }
        return options.getCountry || { code: 'IN', name: 'India' };
    }

    function setStatus(state, message = '', badgeText = '') {
        if (pinEl) {
            pinEl.classList.remove('is-valid', 'is-invalid');
        }
        if (badgeEl) {
            badgeEl.className = 'pincode-status-badge';
        }
        if (feedbackEl) {
            feedbackEl.className = 'pincode-feedback-msg text-start';
        }

        if (state === 'loading') {
            if (spinnerEl) spinnerEl.style.display = 'block';
            if (iconEl) iconEl.innerHTML = '';
            if (badgeEl) {
                badgeEl.textContent = 'Checking...';
                badgeEl.classList.add('loading');
                badgeEl.style.display = 'inline-flex';
            }
            if (feedbackEl) feedbackEl.style.display = 'none';
        } else if (state === 'valid') {
            if (spinnerEl) spinnerEl.style.display = 'none';
            if (iconEl) {
                iconEl.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
            }
            if (pinEl) pinEl.classList.add('is-valid');
            if (badgeEl) {
                badgeEl.textContent = badgeText || 'Valid PIN';
                badgeEl.classList.add('valid');
                badgeEl.style.display = 'inline-flex';
            }
            if (feedbackEl) {
                if (message) {
                    feedbackEl.textContent = message;
                    feedbackEl.classList.add('valid');
                    feedbackEl.style.display = 'block';
                } else {
                    feedbackEl.style.display = 'none';
                }
            }
        } else if (state === 'invalid') {
            if (spinnerEl) spinnerEl.style.display = 'none';
            if (iconEl) {
                iconEl.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;
            }
            if (pinEl) pinEl.classList.add('is-invalid');
            if (badgeEl) {
                badgeEl.textContent = badgeText || 'Invalid';
                badgeEl.classList.add('invalid');
                badgeEl.style.display = 'inline-flex';
            }
            if (feedbackEl) {
                if (message) {
                    feedbackEl.textContent = message;
                    feedbackEl.classList.add('invalid');
                    feedbackEl.style.display = 'block';
                } else {
                    feedbackEl.style.display = 'none';
                }
            }
        } else {
            if (spinnerEl) spinnerEl.style.display = 'none';
            if (iconEl) iconEl.innerHTML = '';
            if (badgeEl) badgeEl.style.display = 'none';
            if (feedbackEl) feedbackEl.style.display = 'none';
        }
    }

    function applyResult(result) {
        if (result && result.valid && result.city) {
            setStatus('valid', result.message, result.badge);
            if (cityEl) {
                cityEl.value = result.city;
                cityEl.readOnly = true;
                cityEl.classList.remove(pulseClass);
                void cityEl.offsetWidth; // Force DOM reflow
                cityEl.classList.add(pulseClass);
            }
            if (typeof options.onValid === 'function') {
                options.onValid(result);
            }
        } else {
            setStatus('invalid', result ? result.message : '', result ? result.badge : '');
            if (cityEl) {
                if (cityEl.readOnly) {
                    cityEl.value = '';
                }
                cityEl.readOnly = false;
            }
            if (typeof options.onInvalid === 'function') {
                options.onInvalid(result);
            }
        }
    }

    async function validateAndFetch(val, country) {
        const rawPin = (val || '').trim();
        if (!rawPin) {
            setStatus('idle');
            if (cityEl) {
                if (cityEl.readOnly) cityEl.value = '';
                cityEl.readOnly = false;
            }
            return;
        }

        setStatus('loading');
        const result = await lookupPincode(rawPin, country.code, country.name);
        if (!result) return;
        applyResult(result);
    }

    function triggerLookup(immediate = false) {
        clearTimeout(debounceTimer);
        if (!pinEl) return;
        const val = pinEl.value.trim();

        if (!val) {
            setStatus('idle');
            if (cityEl && cityEl.readOnly) {
                cityEl.value = '';
                cityEl.readOnly = false;
            }
            return;
        }

        const country = getCountryObj();
        const code = (country.code || 'IN').toUpperCase();

        if (code === 'IN') {
            const digits = val.replace(/\D/g, '');
            if (digits.length < 6 && !immediate) {
                setStatus('idle');
                return;
            }
        } else if (val.length < 2 && !immediate) {
            setStatus('idle');
            return;
        }

        if (immediate) {
            validateAndFetch(val, country);
        } else {
            debounceTimer = setTimeout(() => {
                validateAndFetch(val, country);
            }, 400);
        }
    }

    function updatePlaceholder(country) {
        if (!pinEl) return;
        const target = country || getCountryObj();
        const code = (target.code || 'IN').toUpperCase();
        if (code === 'IN') {
            pinEl.placeholder = "Enter 6-digit PIN code (e.g. 365601)...";
        } else if (code === 'US') {
            pinEl.placeholder = "Enter 5-digit ZIP code (e.g. 90210)...";
        } else if (code === 'GB') {
            pinEl.placeholder = "Enter UK Postcode (e.g. SW1A 1AA)...";
        } else {
            pinEl.placeholder = `Enter postal code for ${target.name || 'country'}...`;
        }
    }

    // Attach event listeners to pincode input
    if (pinEl) {
        pinEl.addEventListener('input', () => triggerLookup(false));
        pinEl.addEventListener('blur', () => {
            if (pinEl.value.trim().length > 0) {
                triggerLookup(true);
            }
        });
        pinEl.addEventListener('change', () => triggerLookup(true));
    }

    // Guard form submit: user cannot submit if city input is empty
    if (formEl && cityEl) {
        formEl.addEventListener('submit', function (e) {
            if (!cityEl.value.trim()) {
                e.preventDefault();
                cityEl.focus();
                if (typeof cityEl.reportValidity === 'function') {
                    cityEl.reportValidity();
                }
                alert('Please enter or verify a valid City before submitting the form.');
            }
        });
    }

    return {
        triggerLookup,
        updatePlaceholder,
        setStatus,
        reset: () => {
            setStatus('idle');
            if (cityEl) {
                cityEl.value = '';
                cityEl.readOnly = false;
            }
        }
    };
}

// Expose globally on window as well
window.fetchCountryList = fetchCountryList;
window.lookupPincode = lookupPincode;
window.attachPincodeAutofill = attachPincodeAutofill;
