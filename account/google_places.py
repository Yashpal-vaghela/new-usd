"""
Small client for Google Places API (New), used to keep clinic opening hours in sync.

Billing (India pricing):
  - search_places()    -> Text Search Pro          (35,000 free calls/month)
  - get_weekly_hours() -> Place Details Enterprise (7,000 free calls/month)
Keep the field masks below as they are: adding fields such as rating/reviews
moves every call into a more expensive SKU.
"""
import httpx
from django.conf import settings

BASE_URL = "https://places.googleapis.com/v1"
TIMEOUT_SECONDS = 15

SEARCH_FIELD_MASK = "places.id,places.displayName,places.formattedAddress"
HOURS_FIELD_MASK = "regularOpeningHours,businessStatus"

# Google's English day names -> Dentist model field names
DAY_FIELDS = {
    "Monday": "Mon",
    "Tuesday": "Tue",
    "Wednesday": "Wed",
    "Thursday": "Thu",
    "Friday": "Fri",
    "Saturday": "Sat",
    "Sunday": "Sun",
}

# Google uses narrow/thin no-break spaces in times ("9:30 AM – 1:30 PM")
_ODD_SPACES = str.maketrans({" ": " ", " ": " ", " ": " "})


class PlacesError(Exception):
    """A single Google request failed (bad Place ID, network error, ...)."""


class PlacesConfigError(PlacesError):
    """Every request will fail (missing/invalid API key, API not enabled, billing off)."""


def _headers(field_mask):
    api_key = getattr(settings, "GOOGLE_PLACES_API_KEY", None)
    if not api_key:
        raise PlacesConfigError("GOOGLE_PLACES_API_KEY is not set in .env")
    return {"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": field_mask}


def _send(method, url, field_mask, **kwargs):
    try:
        resp = httpx.request(method, url, headers=_headers(field_mask), timeout=TIMEOUT_SECONDS, **kwargs)
    except httpx.HTTPError as exc:
        raise PlacesError(f"Network error: {exc}") from exc

    if resp.status_code == 200:
        return resp.json()

    try:
        message = resp.json()["error"]["message"]
    except Exception:
        message = resp.text[:300]
    error = f"HTTP {resp.status_code}: {message}"
    # 403 = API not enabled / billing off / key restricted; "API key not valid" comes back as 400
    if resp.status_code == 403 or "API key" in message:
        raise PlacesConfigError(error)
    raise PlacesError(error)


def search_places(query, lat=None, lng=None, max_results=3):
    """Text-search Google Maps. Returns a list of {id, displayName, formattedAddress}."""
    body = {"textQuery": query, "languageCode": "en", "regionCode": "IN", "pageSize": max_results}
    if lat is not None and lng is not None:
        body["locationBias"] = {
            "circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 5000.0}
        }
    data = _send("POST", f"{BASE_URL}/places:searchText", SEARCH_FIELD_MASK, json=body)
    return data.get("places", [])


# Google period day numbers (0 = Sunday) -> Dentist model field names
_PERIOD_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
_DAY_MIN = 24 * 60
_WEEK_MIN = 7 * _DAY_MIN


def _clock(minutes):
    """540 -> '9', 570 -> '9:30' (Google Maps drops ':00')."""
    h, m = divmod(minutes % _DAY_MIN, 60)
    return f"{h % 12 or 12}" + (f":{m:02d}" if m else "")


def _meridiem(minutes):
    return "am" if (minutes % _DAY_MIN) < 720 else "pm"


def _fmt_range(start, end):
    """
    Google Maps style with spaced dash: '9:30 am – 7:30 pm', '12 – 7:30 am', '9:30 am – 12 am'.
    The start's am/pm is dropped only when both ends share it on the same day.
    """
    same_half = end < _DAY_MIN and _meridiem(start) == _meridiem(end)
    left = _clock(start) if same_half else f"{_clock(start)} {_meridiem(start)}"
    return f"{left} – {_clock(end)} {_meridiem(end)}"


def parse_periods(periods):
    """
    Build per-day hours from regularOpeningHours.periods, splitting overnight periods
    at midnight the way Google Maps shows them:
      Sun 9:30 -> Mon 7:30  =>  Sun "9:30 am–12 am", Mon "12–7:30 am, ..."
    Returns {} when periods can't be used (caller falls back to weekdayDescriptions).
    """
    if not periods:
        return {}
    # A single period without "close" means open 24 hours, every day
    if len(periods) == 1 and "close" not in periods[0]:
        return {day: "Open 24 hours" for day in _PERIOD_DAYS}

    segments = {day: [] for day in range(7)}
    for p in periods:
        o, c = p.get("open"), p.get("close")
        if not o or not c:
            return {}
        start = o.get("day", 0) * _DAY_MIN + o.get("hour", 0) * 60 + o.get("minute", 0)
        end = c.get("day", 0) * _DAY_MIN + c.get("hour", 0) * 60 + c.get("minute", 0)
        if end <= start:          # wraps past Saturday night into Sunday
            end += _WEEK_MIN
        while start < end:
            day_start = start - start % _DAY_MIN
            seg_end = min(end, day_start + _DAY_MIN)
            segments[(day_start // _DAY_MIN) % 7].append((start % _DAY_MIN, seg_end - day_start))
            start = seg_end

    hours = {}
    for day, segs in segments.items():
        segs.sort()
        if not segs:
            text = "Closed"
        elif segs == [(0, _DAY_MIN)]:
            text = "Open 24 hours"
        else:
            text = ", ".join(_fmt_range(a, b) for a, b in segs)
        hours[_PERIOD_DAYS[day]] = text
    return hours


def parse_weekday_descriptions(descriptions):
    """
    ["Monday: 9:30 AM – 1:30 PM, 4:30 – 8:30 PM", "Sunday: Closed", ...]
    -> {"Mon": "9:30 AM – 1:30 PM, 4:30 – 8:30 PM", "Sun": "Closed", ...}
    """
    hours = {}
    for line in descriptions:
        day, sep, value = line.translate(_ODD_SPACES).partition(":")
        field = DAY_FIELDS.get(day.strip())
        if sep and field:
            hours[field] = " ".join(value.split())
    return hours


def get_weekly_hours(place_id):
    """
    Returns (hours, business_status) for a Place ID.
    hours is {"Mon": "...", ..., "Sun": "..."}; empty if the clinic has no hours on Google.
    business_status is e.g. "OPERATIONAL", "CLOSED_TEMPORARILY", "CLOSED_PERMANENTLY" or None.
    """
    data = _send("GET", f"{BASE_URL}/places/{place_id}", HOURS_FIELD_MASK, params={"languageCode": "en"})
    opening = data.get("regularOpeningHours") or {}
    hours = parse_periods(opening.get("periods")) or parse_weekday_descriptions(opening.get("weekdayDescriptions") or [])
    return hours, data.get("businessStatus")
