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
 * 2. Country-Specific Validation Rules for Phone and Postal/PIN codes
 */
const COUNTRY_VALIDATION_RULES = {
    IN: {
        name: "India",
        dialCode: "+91",
        phone: {
            exactDigits: 10,
            minDigits: 10,
            maxDigits: 10,
            regex: /^[6-9]\d{9}$/,
            digitsOnly: true,
            placeholder: "Enter 10-digit mobile number...",
            emptyMsg: "Indian mobile number is required.",
            lengthMsg: "Indian mobile number must be exactly 10 digits.",
            formatMsg: "Indian mobile number must start with 6, 7, 8, or 9."
        },
        postal: {
            exactLength: 6,
            maxLength: 6,
            regex: /^[1-9]\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 6-digit PIN code (e.g. 365601)...",
            emptyMsg: "PIN code is required.",
            formatMsg: "Indian PIN code must be exactly 6 numeric digits."
        }
    },
    US: {
        name: "United States",
        dialCode: "+1",
        phone: {
            exactDigits: 10,
            minDigits: 10,
            maxDigits: 10,
            regex: /^[2-9]\d{2}[2-9]\d{6}$/,
            digitsOnly: true,
            placeholder: "Enter 10-digit phone number (e.g. 2125550199)...",
            emptyMsg: "Phone number is required.",
            lengthMsg: "US phone number must be exactly 10 digits.",
            formatMsg: "Please enter a valid 10-digit US phone number."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit ZIP code (e.g. 90210)...",
            emptyMsg: "ZIP code is required.",
            formatMsg: "US ZIP code must be exactly 5 digits."
        }
    },
    CA: {
        name: "Canada",
        dialCode: "+1",
        phone: {
            exactDigits: 10,
            minDigits: 10,
            maxDigits: 10,
            regex: /^[2-9]\d{9}$/,
            digitsOnly: true,
            placeholder: "Enter 10-digit phone number (e.g. 4165550199)...",
            emptyMsg: "Phone number is required.",
            lengthMsg: "Canadian phone number must be exactly 10 digits.",
            formatMsg: "Please enter a valid 10-digit Canadian phone number."
        },
        postal: {
            maxLength: 7,
            regex: /^[A-CEGHJ-NPR-TVXY]\d[A-CEGHJ-NPR-TV-Z]\s*\d[A-CEGHJ-NPR-TV-Z]\d$/i,
            digitsOnly: false,
            placeholder: "Enter postal code (e.g. K1A 0B1)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Please enter a valid Canadian postal code (e.g. K1A 0B1)."
        }
    },
    GB: {
        name: "United Kingdom",
        dialCode: "+44",
        phone: {
            exactDigits: 10,
            minDigits: 10,
            maxDigits: 10,
            regex: /^[1-9]\d{9}$/,
            digitsOnly: true,
            placeholder: "Enter 10-digit phone number (e.g. 7123456789)...",
            emptyMsg: "Phone number is required.",
            lengthMsg: "UK phone number must be exactly 10 digits.",
            formatMsg: "UK phone number must be 10 digits (e.g. 7123456789)."
        },
        postal: {
            maxLength: 8,
            regex: /^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$/i,
            digitsOnly: false,
            placeholder: "Enter UK Postcode (e.g. SW1A 1AA)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Please enter a valid UK postcode (e.g. SW1A 1AA)."
        }
    },
    AE: {
        name: "United Arab Emirates",
        dialCode: "+971",
        phone: {
            exactDigits: 9,
            minDigits: 9,
            maxDigits: 9,
            regex: /^[1-9]\d{8}$/,
            digitsOnly: true,
            placeholder: "Enter 9-digit mobile number (e.g. 501234567)...",
            emptyMsg: "Phone number is required.",
            lengthMsg: "UAE phone number must be exactly 9 digits.",
            formatMsg: "UAE phone number must be 9 digits (e.g. 501234567)."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit postal code (e.g. 00000)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "UAE postal code must be exactly 5 digits."
        }
    },
    AU: {
        name: "Australia",
        dialCode: "+61",
        phone: {
            exactDigits: 9,
            minDigits: 9,
            maxDigits: 9,
            regex: /^[1-9]\d{8}$/,
            digitsOnly: true,
            placeholder: "Enter 9-digit phone number (e.g. 412345678)...",
            emptyMsg: "Phone number is required.",
            lengthMsg: "Australian phone number must be exactly 9 digits.",
            formatMsg: "Australian phone number must be 9 digits (e.g. 412345678)."
        },
        postal: {
            exactLength: 4,
            maxLength: 4,
            regex: /^\d{4}$/,
            digitsOnly: true,
            placeholder: "Enter 4-digit postal code (e.g. 2000)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Australian postal code must be exactly 4 digits."
        }
    },
    SA: {
        name: "Saudi Arabia",
        dialCode: "+966",
        phone: {
            exactDigits: 9,
            minDigits: 9,
            maxDigits: 9,
            regex: /^5\d{8}$/,
            digitsOnly: true,
            placeholder: "Enter 9-digit mobile number (e.g. 512345678)...",
            emptyMsg: "Phone number is required.",
            lengthMsg: "Saudi phone number must be exactly 9 digits.",
            formatMsg: "Saudi mobile number must start with 5 and be 9 digits."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit postal code (e.g. 11564)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Saudi postal code must be exactly 5 digits."
        }
    },
    DE: {
        name: "Germany",
        dialCode: "+49",
        phone: {
            minDigits: 10,
            maxDigits: 11,
            regex: /^[1-9]\d{9,10}$/,
            digitsOnly: true,
            placeholder: "Enter 10-11 digit phone number...",
            emptyMsg: "Phone number is required.",
            lengthMsg: "German phone number must be 10 to 11 digits.",
            formatMsg: "Please enter a valid German phone number."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit postal code (e.g. 10115)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "German postal code must be exactly 5 digits."
        }
    },
    FR: {
        name: "France",
        dialCode: "+33",
        phone: {
            exactDigits: 9,
            minDigits: 9,
            maxDigits: 9,
            regex: /^[1-9]\d{8}$/,
            digitsOnly: true,
            placeholder: "Enter 9-digit phone number (e.g. 612345678)...",
            emptyMsg: "Phone number is required.",
            lengthMsg: "French phone number must be exactly 9 digits.",
            formatMsg: "Please enter a valid 9-digit French phone number."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit postal code (e.g. 75001)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "French postal code must be exactly 5 digits."
        }
    },
    SG: {
        name: "Singapore",
        dialCode: "+65",
        phone: {
            exactDigits: 8,
            minDigits: 8,
            maxDigits: 8,
            regex: /^[89]\d{7}$/,
            digitsOnly: true,
            placeholder: "Enter 8-digit phone number (e.g. 81234567)...",
            emptyMsg: "Phone number is required.",
            lengthMsg: "Singapore phone number must be exactly 8 digits.",
            formatMsg: "Singapore phone number must start with 8 or 9 (8 digits)."
        },
        postal: {
            exactLength: 6,
            maxLength: 6,
            regex: /^\d{6}$/,
            digitsOnly: true,
            placeholder: "Enter 6-digit postal code (e.g. 238823)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Singapore postal code must be exactly 6 digits."
        }
    },
    OM: {
        name: "Oman",
        dialCode: "+968",
        phone: {
            exactDigits: 8,
            minDigits: 8,
            maxDigits: 8,
            regex: /^[79]\d{7}$/,
            digitsOnly: true,
            placeholder: "Enter 8-digit phone number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Oman phone number must be 8 digits."
        },
        postal: {
            exactLength: 3,
            maxLength: 3,
            regex: /^\d{3}$/,
            digitsOnly: true,
            placeholder: "Enter 3-digit postal code (e.g. 111)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Oman postal code must be exactly 3 digits."
        }
    },
    QA: {
        name: "Qatar",
        dialCode: "+974",
        phone: {
            exactDigits: 8,
            minDigits: 8,
            maxDigits: 8,
            regex: /^[3567]\d{7}$/,
            digitsOnly: true,
            placeholder: "Enter 8-digit phone number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Qatar phone number must be 8 digits."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit postal code...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Qatar postal code must be exactly 5 digits."
        }
    },
    KW: {
        name: "Kuwait",
        dialCode: "+965",
        phone: {
            exactDigits: 8,
            minDigits: 8,
            maxDigits: 8,
            regex: /^[569]\d{7}$/,
            digitsOnly: true,
            placeholder: "Enter 8-digit phone number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Kuwait phone number must be 8 digits."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit postal code...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Kuwait postal code must be 5 digits."
        }
    },
    BH: {
        name: "Bahrain",
        dialCode: "+973",
        phone: {
            exactDigits: 8,
            minDigits: 8,
            maxDigits: 8,
            regex: /^[36]\d{7}$/,
            digitsOnly: true,
            placeholder: "Enter 8-digit phone number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Bahrain phone number must be 8 digits."
        },
        postal: {
            minLength: 3,
            maxLength: 4,
            regex: /^\d{3,4}$/,
            digitsOnly: true,
            placeholder: "Enter postal / block code (e.g. 316)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Bahrain postal code must be 3 to 4 digits."
        }
    },
    NP: {
        name: "Nepal",
        dialCode: "+977",
        phone: {
            exactDigits: 10,
            minDigits: 10,
            maxDigits: 10,
            regex: /^9[78]\d{8}$/,
            digitsOnly: true,
            placeholder: "Enter 10-digit mobile number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Nepal mobile number must be 10 digits starting with 98 or 97."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit postal code (e.g. 44600)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Nepal postal code must be 5 digits."
        }
    },
    BD: {
        name: "Bangladesh",
        dialCode: "+880",
        phone: {
            exactDigits: 10,
            minDigits: 10,
            maxDigits: 10,
            regex: /^1[3-9]\d{8}$/,
            digitsOnly: true,
            placeholder: "Enter 10-digit mobile number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Bangladesh mobile number must be 10 digits starting with 1."
        },
        postal: {
            exactLength: 4,
            maxLength: 4,
            regex: /^\d{4}$/,
            digitsOnly: true,
            placeholder: "Enter 4-digit postal code (e.g. 1205)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Bangladesh postal code must be 4 digits."
        }
    },
    PK: {
        name: "Pakistan",
        dialCode: "+92",
        phone: {
            exactDigits: 10,
            minDigits: 10,
            maxDigits: 10,
            regex: /^3\d{9}$/,
            digitsOnly: true,
            placeholder: "Enter 10-digit mobile number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Pakistan mobile number must be 10 digits starting with 3."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit postal code (e.g. 44000)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Pakistan postal code must be 5 digits."
        }
    },
    LK: {
        name: "Sri Lanka",
        dialCode: "+94",
        phone: {
            exactDigits: 9,
            minDigits: 9,
            maxDigits: 9,
            regex: /^7\d{8}$/,
            digitsOnly: true,
            placeholder: "Enter 9-digit mobile number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Sri Lanka mobile number must be 9 digits starting with 7."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit postal code (e.g. 00100)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Sri Lanka postal code must be 5 digits."
        }
    },
    MY: {
        name: "Malaysia",
        dialCode: "+60",
        phone: {
            minDigits: 9,
            maxDigits: 10,
            regex: /^1\d{8,9}$/,
            digitsOnly: true,
            placeholder: "Enter 9-10 digit mobile number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Malaysia mobile number must be 9 to 10 digits starting with 1."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit postal code (e.g. 50450)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Malaysia postal code must be 5 digits."
        }
    },
    IT: {
        name: "Italy",
        dialCode: "+39",
        phone: {
            minDigits: 9,
            maxDigits: 10,
            regex: /^3\d{8,9}$/,
            digitsOnly: true,
            placeholder: "Enter 9-10 digit mobile number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Italian mobile number must be 9 to 10 digits."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit postal code (e.g. 00185)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Italian postal code must be 5 digits."
        }
    },
    ES: {
        name: "Spain",
        dialCode: "+34",
        phone: {
            exactDigits: 9,
            minDigits: 9,
            maxDigits: 9,
            regex: /^[67]\d{8}$/,
            digitsOnly: true,
            placeholder: "Enter 9-digit phone number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Spanish phone number must be 9 digits starting with 6 or 7."
        },
        postal: {
            exactLength: 5,
            maxLength: 5,
            regex: /^\d{5}$/,
            digitsOnly: true,
            placeholder: "Enter 5-digit postal code (e.g. 28001)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Spanish postal code must be 5 digits."
        }
    },
    NL: {
        name: "Netherlands",
        dialCode: "+31",
        phone: {
            exactDigits: 9,
            minDigits: 9,
            maxDigits: 9,
            regex: /^6\d{8}$/,
            digitsOnly: true,
            placeholder: "Enter 9-digit mobile number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Dutch mobile number must be 9 digits starting with 6."
        },
        postal: {
            maxLength: 7,
            regex: /^\d{4}\s?[A-Z]{2}$/i,
            digitsOnly: false,
            placeholder: "Enter postal code (e.g. 1012 AB)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Dutch postal code must be 4 digits followed by 2 letters."
        }
    },
    JP: {
        name: "Japan",
        dialCode: "+81",
        phone: {
            exactDigits: 10,
            minDigits: 10,
            maxDigits: 10,
            regex: /^[789]0\d{8}$/,
            digitsOnly: true,
            placeholder: "Enter 10-digit mobile number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Japanese mobile number must be 10 digits."
        },
        postal: {
            maxLength: 8,
            regex: /^\d{3}-?\d{4}$/,
            digitsOnly: false,
            placeholder: "Enter postal code (e.g. 100-0001)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Japanese postal code must be 7 digits (e.g. 100-0001)."
        }
    },
    CN: {
        name: "China",
        dialCode: "+86",
        phone: {
            exactDigits: 11,
            minDigits: 11,
            maxDigits: 11,
            regex: /^1[3-9]\d{9}$/,
            digitsOnly: true,
            placeholder: "Enter 11-digit mobile number...",
            emptyMsg: "Phone number is required.",
            formatMsg: "Chinese mobile number must be 11 digits starting with 1."
        },
        postal: {
            exactLength: 6,
            maxLength: 6,
            regex: /^\d{6}$/,
            digitsOnly: true,
            placeholder: "Enter 6-digit postal code (e.g. 100000)...",
            emptyMsg: "Postal code is required.",
            formatMsg: "Chinese postal code must be 6 digits."
        }
    }
};

/**
 * Helper to get country validation configuration with safe fallback
 */
function getCountryRule(countryCode, countryName = "") {
    const code = (countryCode || "IN").toUpperCase();
    if (COUNTRY_VALIDATION_RULES[code]) {
        return COUNTRY_VALIDATION_RULES[code];
    }
    const name = countryName || code;
    return {
        name: name,
        dialCode: "",
        phone: {
            minDigits: 7,
            maxDigits: 15,
            regex: /^[1-9]\d{6,14}$/,
            digitsOnly: true,
            placeholder: `Enter phone number for ${name}...`,
            emptyMsg: "Phone number is required.",
            lengthMsg: `Phone number for ${name} must be 7 to 15 digits.`,
            formatMsg: `Please enter a valid phone number (7-15 digits) for ${name}.`
        },
        postal: {
            minLength: 3,
            maxLength: 10,
            regex: /^[A-Za-z0-9\s-]{3,10}$/,
            digitsOnly: false,
            placeholder: `Enter postal code for ${name}...`,
            emptyMsg: "Postal code is required.",
            formatMsg: `Please enter a valid postal code (3-10 characters) for ${name}.`
        }
    };
}

/**
 * Validate a phone number string against country rules
 */
function validatePhoneNumber(rawPhone, countryCode = 'IN', countryName = 'India') {
    const rule = getCountryRule(countryCode, countryName).phone;
    const digits = (rawPhone || '').replace(/\D/g, '');

    if (!digits) {
        return {
            valid: false,
            empty: true,
            message: rule.emptyMsg || 'Phone number is required.',
            badge: 'Required'
        };
    }

    // Check if alphabetic or invalid characters were entered
    if (/[a-zA-Z]/.test(rawPhone)) {
        return {
            valid: false,
            message: 'Phone number cannot contain alphabets.',
            badge: 'Invalid'
        };
    }

    if (rule.exactDigits && digits.length !== rule.exactDigits) {
        return {
            valid: false,
            message: rule.lengthMsg || `Phone number must be exactly ${rule.exactDigits} digits.`,
            badge: `${digits.length}/${rule.exactDigits}`
        };
    }

    if (rule.minDigits && digits.length < rule.minDigits) {
        return {
            valid: false,
            message: rule.lengthMsg || `Phone number must be at least ${rule.minDigits} digits.`,
            badge: `${digits.length}/${rule.minDigits}+`
        };
    }

    if (rule.maxDigits && digits.length > rule.maxDigits) {
        return {
            valid: false,
            message: rule.lengthMsg || `Phone number must not exceed ${rule.maxDigits} digits.`,
            badge: 'Too Long'
        };
    }

    if (rule.regex && !rule.regex.test(digits)) {
        return {
            valid: false,
            message: rule.formatMsg || 'Please enter a valid phone number.',
            badge: 'Invalid'
        };
    }

    return {
        valid: true,
        message: '✓ Valid phone number',
        badge: 'Valid Phone'
    };
}

/**
 * Validate a postal / pincode string against country rules
 */
function validatePostalCode(rawPin, countryCode = 'IN', countryName = 'India') {
    const rule = getCountryRule(countryCode, countryName).postal;
    const trimmed = (rawPin || '').trim();

    if (!trimmed) {
        return {
            valid: false,
            empty: true,
            message: rule.emptyMsg || 'PIN / Postal code is required.',
            badge: 'Required'
        };
    }

    const code = (countryCode || 'IN').toUpperCase();

    // India specific strict rule: exactly 6 digits, digits only, no alphabets or invalid chars
    if (code === 'IN') {
        if (/\D/.test(trimmed)) {
            return {
                valid: false,
                message: 'Indian PIN code must contain only 6 numeric digits (no alphabets or symbols).',
                badge: 'Invalid PIN'
            };
        }
        if (trimmed.length !== 6) {
            return {
                valid: false,
                message: 'Indian PIN code must be exactly 6 digits.',
                badge: `${trimmed.length}/6`
            };
        }
        if (!/^[1-9]\d{5}$/.test(trimmed)) {
            return {
                valid: false,
                message: 'Indian PIN code cannot start with 0.',
                badge: 'Invalid PIN'
            };
        }
        return {
            valid: true,
            message: '✓ Valid PIN code format',
            badge: 'Valid PIN'
        };
    }

    // Other countries
    if (rule.digitsOnly) {
        if (/\D/.test(trimmed)) {
            return {
                valid: false,
                message: `Postal code for ${countryName} must contain only numeric digits.`,
                badge: 'Digits Only'
            };
        }
        if (rule.exactLength && trimmed.length !== rule.exactLength) {
            return {
                valid: false,
                message: rule.formatMsg || `Postal code must be exactly ${rule.exactLength} digits.`,
                badge: `${trimmed.length}/${rule.exactLength}`
            };
        }
        if (rule.regex && !rule.regex.test(trimmed)) {
            return {
                valid: false,
                message: rule.formatMsg || `Invalid postal code for ${countryName}.`,
                badge: 'Invalid'
            };
        }
    } else {
        if (rule.regex && !rule.regex.test(trimmed)) {
            return {
                valid: false,
                message: rule.formatMsg || `Invalid postal code format for ${countryName}.`,
                badge: 'Invalid'
            };
        }
    }

    return {
        valid: true,
        message: '✓ Valid postal code format',
        badge: 'Valid Code'
    };
}

/**
 * 3. Shared Pincode Cache and Abort Controller
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

    const code = (countryCode || 'IN').toUpperCase();

    // 1. First run format validation
    const formatCheck = validatePostalCode(rawPin, code, countryName);
    if (!formatCheck.valid) {
        return formatCheck;
    }

    const cacheKey = `${code}_${rawPin.toUpperCase()}`;
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
            const url = `https://nominatim.openstreetmap.org/search?postalcode=${encodeURIComponent(rawPin)}&countrycodes=${code.toLowerCase()}&format=json&addressdetails=1`;
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
    if (code === 'IN') {
        const cleanPin = rawPin.replace(/\D/g, '');
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
        const res = await fetch(`https://api.zippopotam.us/${code.toLowerCase()}/${cleanPin}`, { signal });
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
 * 4. Centralized Phone UI Attachment Helper
 * Handles keystroke prevention (digits only), max-length limiting,
 * dynamic updates when country changes, feedback messages, and valid/invalid styling.
 */
function attachPhoneValidation(options) {
    function resolve(el) {
        if (!el) return null;
        if (typeof el === 'string') return document.querySelector(el);
        return el;
    }

    const phoneEl = resolve(options.phoneInput);
    const fullPhoneEl = resolve(options.fullPhoneInput);
    const fieldBoxEl = resolve(options.fieldBox) || (phoneEl ? phoneEl.closest('.phone_field_box, .country-phone-wrapper, .input_filds_and_icon_main') : null);
    const iconEl = resolve(options.statusIcon);
    const badgeEl = resolve(options.statusBadge);
    const feedbackEl = resolve(options.feedback);

    function getCountryObj() {
        if (typeof options.getCountry === 'function') {
            return options.getCountry() || { code: 'IN', name: 'India', dialCode: '+91' };
        }
        return options.getCountry || { code: 'IN', name: 'India', dialCode: '+91' };
    }

    function updateFullPhone() {
        if (!phoneEl) return;
        const country = getCountryObj();
        const number = phoneEl.value.trim();
        if (fullPhoneEl) {
            if (number) {
                if (number.startsWith('+')) {
                    fullPhoneEl.value = number;
                } else {
                    fullPhoneEl.value = `${country.dialCode || ''} ${number}`.trim();
                }
            } else {
                fullPhoneEl.value = '';
            }
        }
    }

    function setStatus(state, message = '', badgeText = '') {
        if (phoneEl) {
            phoneEl.classList.remove('is-valid', 'is-invalid');
        }
        if (fieldBoxEl) {
            fieldBoxEl.classList.remove('is-valid', 'is-invalid');
        }
        if (badgeEl) {
            badgeEl.className = 'phone-status-badge';
        }
        if (feedbackEl) {
            feedbackEl.className = 'phone-feedback-msg text-start';
        }

        if (state === 'valid') {
            if (iconEl) {
                iconEl.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
            }
            if (phoneEl) phoneEl.classList.add('is-valid');
            if (fieldBoxEl) fieldBoxEl.classList.add('is-valid');
            if (badgeEl) {
                badgeEl.textContent = badgeText || 'Valid Phone';
                badgeEl.classList.add('valid');
                badgeEl.style.display = 'inline-flex';
            }
            if (feedbackEl) {
                feedbackEl.style.display = 'none';
            }
            if (typeof options.onValid === 'function') {
                options.onValid();
            }
        } else if (state === 'invalid') {
            if (iconEl) {
                iconEl.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;
            }
            if (phoneEl) phoneEl.classList.add('is-invalid');
            if (fieldBoxEl) fieldBoxEl.classList.add('is-invalid');
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
            if (typeof options.onInvalid === 'function') {
                options.onInvalid(message);
            }
        } else {
            // idle
            if (iconEl) iconEl.innerHTML = '';
            if (badgeEl) badgeEl.style.display = 'none';
            if (feedbackEl) feedbackEl.style.display = 'none';
        }
    }

    function validate(showErrorOnEmpty = false) {
        if (!phoneEl) return false;
        const country = getCountryObj();
        const raw = phoneEl.value.trim();

        if (!raw) {
            if (showErrorOnEmpty) {
                const rule = getCountryRule(country.code, country.name).phone;
                setStatus('invalid', rule.emptyMsg || 'Please enter your phone number.', 'Required');
                return false;
            }
            setStatus('idle');
            return false;
        }

        const res = validatePhoneNumber(raw, country.code, country.name);
        if (res.valid) {
            setStatus('valid', res.message, res.badge);
            return true;
        } else {
            setStatus('invalid', res.message, res.badge);
            return false;
        }
    }

    function updateCountry(country) {
        if (!phoneEl) return;
        const target = country || getCountryObj();
        const rule = getCountryRule(target.code, target.name).phone;

        phoneEl.placeholder = rule.placeholder || `Enter phone number for ${target.name || 'country'}...`;
        if (rule.maxDigits) {
            phoneEl.maxLength = rule.maxDigits;
        } else {
            phoneEl.removeAttribute('maxLength');
        }

        // Sanitize current value under new country rules
        let cleaned = phoneEl.value.replace(/\D/g, '');
        if (rule.maxDigits && cleaned.length > rule.maxDigits) {
            cleaned = cleaned.slice(0, rule.maxDigits);
        }
        phoneEl.value = cleaned;
        updateFullPhone();

        if (phoneEl.value.trim().length > 0) {
            validate(true);
        } else {
            setStatus('idle');
        }
    }

    // Keystroke enforcement: numeric digits only
    if (phoneEl) {
        phoneEl.addEventListener('keydown', function (e) {
            const country = getCountryObj();
            const rule = getCountryRule(country.code, country.name).phone;

            // Allowed navigation and editing keys
            const allowedKeys = [
                'Backspace', 'Delete', 'Tab', 'Escape', 'Enter',
                'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown',
                'Home', 'End'
            ];
            if (allowedKeys.includes(e.key)) return;

            // Allow Ctrl/Cmd + shortcuts (A, C, V, X, Z)
            if ((e.ctrlKey || e.metaKey) && ['a', 'c', 'v', 'x', 'z'].includes(e.key.toLowerCase())) {
                return;
            }

            // Block any non-numeric key
            if (!/^\d$/.test(e.key)) {
                e.preventDefault();
                return;
            }

            // Block typing past maxDigits if no text is selected
            if (rule.maxDigits) {
                const currentDigits = phoneEl.value.replace(/\D/g, '');
                const hasSelection = phoneEl.selectionStart !== phoneEl.selectionEnd;
                if (currentDigits.length >= rule.maxDigits && !hasSelection) {
                    e.preventDefault();
                    return;
                }
            }
        });

        phoneEl.addEventListener('input', function () {
            const country = getCountryObj();
            const rule = getCountryRule(country.code, country.name).phone;

            let digits = phoneEl.value.replace(/\D/g, '');

            // Smart handling if pasted with country dial code (e.g. +91 9876543210 -> 919876543210)
            if (country.dialCode) {
                const dialDigits = country.dialCode.replace(/\D/g, '');
                if (dialDigits && digits.startsWith(dialDigits) && digits.length === (dialDigits.length + (rule.exactDigits || rule.minDigits || 10))) {
                    digits = digits.slice(dialDigits.length);
                }
            }

            // Smart handling for national trunk prefix 0 (e.g. UK 07xxx, UAE 05xxx, AU 04xxx, SA 05xxx, FR 06xxx)
            if (digits.startsWith('0') && country.code !== 'IN' && country.code !== 'US' && country.code !== 'CA') {
                if (rule.regex && !rule.regex.source.startsWith('^0')) {
                    digits = digits.replace(/^0+/, '');
                }
            }

            if (rule.maxDigits && digits.length > rule.maxDigits) {
                digits = digits.slice(0, rule.maxDigits);
            }

            if (phoneEl.value !== digits) {
                phoneEl.value = digits;
            }

            updateFullPhone();

            if (digits.length === 0) {
                setStatus('idle');
            } else if (rule.exactDigits && digits.length === rule.exactDigits) {
                validate(false);
            } else if (!rule.exactDigits && rule.minDigits && digits.length >= rule.minDigits) {
                validate(false);
            } else {
                setStatus('idle');
            }
        });

        phoneEl.addEventListener('blur', function () {
            if (phoneEl.value.trim().length > 0) {
                validate(true);
            }
        });
    }

    return {
        validate,
        updateCountry,
        updateFullPhone,
        setStatus,
        showError: (msg) => setStatus('invalid', msg, 'Invalid'),
        isValid: () => {
            if (!phoneEl) return false;
            const country = getCountryObj();
            const res = validatePhoneNumber(phoneEl.value.trim(), country.code, country.name);
            return !!res.valid;
        },
        reset: () => {
            setStatus('idle');
            if (phoneEl) phoneEl.value = '';
            if (fullPhoneEl) fullPhoneEl.value = '';
        }
    };
}

/**
 * 5. Centralized Pincode UI Attachment Helper
 * Handles debouncing, visual status indicators, country-specific keystroke filtering,
 * dynamic city input locking/unlocking, pulse animations, and placeholder updates.
 */
function attachPincodeAutofill(options) {
    function resolve(el) {
        if (!el) return null;
        if (typeof el === 'string') return document.querySelector(el);
        return el;
    }

    const pinEl = resolve(options.pincodeInput);
    const cityEl = resolve(options.cityInput);
    const fieldBoxEl = resolve(options.fieldBox) || (pinEl ? pinEl.closest('.pincode_field_box, .input_filds_and_icon_main') : null);
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
        if (fieldBoxEl) {
            fieldBoxEl.classList.remove('is-valid', 'is-invalid');
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
            if (fieldBoxEl) fieldBoxEl.classList.add('is-valid');
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
            if (fieldBoxEl) fieldBoxEl.classList.add('is-invalid');
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

        // Format validation first
        const formatCheck = validatePostalCode(rawPin, country.code, country.name);
        if (!formatCheck.valid) {
            setStatus('invalid', formatCheck.message, formatCheck.badge);
            if (cityEl && cityEl.readOnly) {
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
        const rule = getCountryRule(country.code, country.name).postal;

        if (rule.exactLength) {
            const digits = rule.digitsOnly ? val.replace(/\D/g, '') : val.trim();
            if (digits.length < rule.exactLength && !immediate) {
                setStatus('idle');
                return;
            }
        } else if (val.length < (rule.minLength || 2) && !immediate) {
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
        const rule = getCountryRule(target.code, target.name).postal;
        pinEl.placeholder = rule.placeholder || `Enter postal code for ${target.name || 'country'}...`;
        if (rule.maxLength) {
            pinEl.maxLength = rule.maxLength;
        } else {
            pinEl.removeAttribute('maxLength');
        }
    }

    function updateCountry(country) {
        if (!pinEl) return;
        const target = country || getCountryObj();
        const rule = getCountryRule(target.code, target.name).postal;

        updatePlaceholder(target);

        // Sanitize current value
        if (rule.digitsOnly) {
            pinEl.value = pinEl.value.replace(/\D/g, '').slice(0, rule.maxLength || 6);
        } else if (rule.maxLength && pinEl.value.length > rule.maxLength) {
            pinEl.value = pinEl.value.slice(0, rule.maxLength);
        }

        if (pinEl.value.trim().length > 0) {
            triggerLookup(true);
        } else {
            setStatus('idle');
        }
    }

    // Attach keystroke enforcement & listeners to pincode input
    if (pinEl) {
        pinEl.addEventListener('keydown', function (e) {
            const country = getCountryObj();
            const rule = getCountryRule(country.code, country.name).postal;

            // Allowed navigation / editing keys
            const allowedKeys = [
                'Backspace', 'Delete', 'Tab', 'Escape', 'Enter',
                'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown',
                'Home', 'End'
            ];
            if (allowedKeys.includes(e.key)) return;

            // Allow Ctrl/Cmd shortcuts
            if ((e.ctrlKey || e.metaKey) && ['a', 'c', 'v', 'x', 'z'].includes(e.key.toLowerCase())) {
                return;
            }

            // If country requires digits only (e.g. India, Australia, Germany, etc.)
            if (rule.digitsOnly) {
                if (!/^\d$/.test(e.key)) {
                    e.preventDefault();
                    return;
                }
                const currentDigits = pinEl.value.replace(/\D/g, '');
                const hasSelection = pinEl.selectionStart !== pinEl.selectionEnd;
                if (rule.maxLength && currentDigits.length >= rule.maxLength && !hasSelection) {
                    e.preventDefault();
                    return;
                }
            } else {
                // For alphanumeric postal codes (e.g. UK, Canada), disallow unwanted special symbols
                if (!/^[a-zA-Z0-9\s-]$/.test(e.key)) {
                    e.preventDefault();
                    return;
                }
                const hasSelection = pinEl.selectionStart !== pinEl.selectionEnd;
                if (rule.maxLength && pinEl.value.length >= rule.maxLength && !hasSelection) {
                    e.preventDefault();
                    return;
                }
            }
        });

        pinEl.addEventListener('input', () => {
            const country = getCountryObj();
            const rule = getCountryRule(country.code, country.name).postal;

            if (rule.digitsOnly) {
                let digits = pinEl.value.replace(/\D/g, '');
                if (rule.maxLength && digits.length > rule.maxLength) {
                    digits = digits.slice(0, rule.maxLength);
                }
                if (pinEl.value !== digits) {
                    pinEl.value = digits;
                }
            } else {
                let cleaned = pinEl.value.replace(/[^a-zA-Z0-9\s-]/g, '');
                if (rule.maxLength && cleaned.length > rule.maxLength) {
                    cleaned = cleaned.slice(0, rule.maxLength);
                }
                if (pinEl.value !== cleaned) {
                    pinEl.value = cleaned;
                }
            }

            triggerLookup(false);
        });

        pinEl.addEventListener('blur', () => {
            if (pinEl.value.trim().length > 0) {
                triggerLookup(true);
            }
        });

        pinEl.addEventListener('change', () => triggerLookup(true));
    }

    // Optional form guard if city is empty
    if (formEl && cityEl) {
        formEl.addEventListener('submit', function (e) {
            if (!cityEl.value.trim()) {
                e.preventDefault();
                cityEl.focus();
                if (typeof cityEl.reportValidity === 'function') {
                    cityEl.reportValidity();
                }
            }
        });
    }

    return {
        triggerLookup,
        updatePlaceholder,
        updateCountry,
        setStatus,
        showError: (msg) => setStatus('invalid', msg, 'Invalid'),
        isValid: () => {
            if (!pinEl) return false;
            const country = getCountryObj();
            const res = validatePostalCode(pinEl.value.trim(), country.code, country.name);
            return !!res.valid;
        },
        reset: () => {
            setStatus('idle');
            if (cityEl) {
                cityEl.value = '';
                cityEl.readOnly = false;
            }
        }
    };
}

// Expose globally on window
window.COUNTRY_VALIDATION_RULES = COUNTRY_VALIDATION_RULES;
window.getCountryRule = getCountryRule;
window.validatePhoneNumber = validatePhoneNumber;
window.validatePostalCode = validatePostalCode;
window.attachPhoneValidation = attachPhoneValidation;
window.attachPincodeAutofill = attachPincodeAutofill;
window.lookupPincode = lookupPincode;
window.fetchCountryList = fetchCountryList;

