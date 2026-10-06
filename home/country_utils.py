"""
Country & Pincode utility functions for Python / Django backend.
Can be imported in views.py or forms.py for validation, sanitization,
and external API checks.
"""
import re
import json
import logging
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)


def clean_pincode(pincode_str):
    """Strip whitespace and retain clean postal code representation."""
    return str(pincode_str or '').strip()


def validate_indian_pin(pin_value):
    """
    Check if a given string is a valid 6-digit Indian PIN code.
    Returns: bool
    """
    digits = re.sub(r'\D', '', str(pin_value or ''))
    return len(digits) == 6


def verify_pincode_india_api(pin_value, timeout=4):
    """
    Look up Indian PIN code using India Post public API on the server side.
    Returns:
        dict: {
            'valid': bool,
            'city': str,
            'state': str,
            'message': str
        }
    """
    clean = re.sub(r'\D', '', str(pin_value or ''))
    if len(clean) != 6:
        return {
            'valid': False,
            'city': '',
            'state': '',
            'message': 'PIN code must be a 6-digit numeric value for India.'
        }

    url = f"https://api.postalpincode.in/pincode/{clean}"
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Django-CountryUtils/1.0'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
            if (
                payload
                and isinstance(payload, list)
                and len(payload) > 0
                and payload[0].get('Status') == 'Success'
                and payload[0].get('PostOffice')
            ):
                po = payload[0]['PostOffice'][0]
                city = po.get('District') or po.get('Block') or po.get('Taluk') or po.get('Name') or ''
                state = po.get('State') or ''
                return {
                    'valid': True,
                    'city': city,
                    'state': state,
                    'message': f"Located: {city}, {state}"
                }
            else:
                return {
                    'valid': False,
                    'city': '',
                    'state': '',
                    'message': 'PIN code not found in postal directory.'
                }
    except Exception as exc:
        logger.warning("Error verifying PIN code against India Post API: %s", exc)
        return {
            'valid': False,
            'city': '',
            'state': '',
            'message': 'Unable to connect to postal verification service.'
        }


def validate_form_city_pincode(pincode, city, country_code='IN'):
    """
    Validates that both pincode and city are provided.
    Enforces that city cannot be empty.
    
    Returns:
        tuple (is_valid: bool, error_message: str or None)
    """
    pincode_clean = clean_pincode(pincode)
    city_clean = str(city or '').strip()

    if not city_clean:
        return False, "City is mandatory. Please provide a valid city name."

    if not pincode_clean:
        return False, "Pincode is mandatory."

    if (country_code or 'IN').upper() == 'IN':
        if not validate_indian_pin(pincode_clean):
            return False, "Please provide a valid 6-digit Indian PIN code."

    return True, None
