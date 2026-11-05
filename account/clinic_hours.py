"""
Sync Mon–Sun opening hours of ACTIVE dentists (status=True) from Google Maps.

Used by:
  - the nightly command       `python manage.py sync_clinic_hours`
  - the Dentist admin buttons "Fetch Google hours (all active)" / "Fetch hours from Google"
    and the "Fetch opening hours from Google" admin action.

A dentist without a google_place_id is linked automatically to the best Google Maps
match for its clinic name + address (shown in the admin message / command output so a
wrong match can be corrected in the "Google place id" field).
"""
from dataclasses import dataclass, field

from django.utils import timezone

from .google_places import DAY_FIELDS, PlacesConfigError, PlacesError, get_weekly_hours, search_places
from .models import Dentist

DAY_ORDER = list(DAY_FIELDS.values())  # Mon ... Sun


def active_dentists():
    return Dentist.objects.filter(status=True).select_related("city").order_by("id")


def build_search_query(dentist):
    name = dentist.clinic_name or dentist.name
    address = dentist.address or ""
    parts = [address] if name.lower() in address.lower() else [name, address]
    if dentist.city and dentist.city.city.lower() not in address.lower():
        parts.append(dentist.city.city)
    return ", ".join(" ".join(p.split()) for p in parts if p and p.strip())


@dataclass
class SyncResult:
    dentist: Dentist
    status: str
    changes: dict = field(default_factory=dict)  # {"Mon": ("old value", "new value")}
    business_status: str = None                  # e.g. "CLOSED_TEMPORARILY"
    linked_place: dict = None                    # Google match, when the Place ID was linked in this run
    error: str = ""

    @property
    def label(self):
        return self.dentist.clinic_name or self.dentist.name

    @property
    def linked_place_text(self):
        if not self.linked_place:
            return ""
        name = (self.linked_place.get("displayName") or {}).get("text", "?")
        return f"{name}, {self.linked_place.get('formattedAddress', '')}"


def link_place_id(dentist, save=True):
    """Find the dentist's clinic on Google Maps and store the top match's Place ID."""
    places = search_places(build_search_query(dentist), dentist.lat, dentist.long, max_results=1)
    if not places:
        return None
    dentist.google_place_id = places[0]["id"]
    if save:
        dentist.save(update_fields=["google_place_id"])
    return places[0]


def sync_dentist_hours(dentist, *, now=None, dry_run=False):
    """
    Fetch one dentist's weekly hours from Google and update Mon–Sun if they changed.
    Inactive dentists are skipped without calling Google.
    Raises PlacesConfigError (bad/missing API key, billing off) so callers can stop the run;
    any other Google error is returned as status "error".
    """
    if not dentist.status:
        return SyncResult(dentist, "inactive")

    now = now or timezone.now()
    linked = None
    try:
        if not dentist.google_place_id:
            linked = link_place_id(dentist, save=not dry_run)
            if not linked:
                return SyncResult(dentist, "not_found")
        hours, business_status = get_weekly_hours(dentist.google_place_id)
    except PlacesConfigError:
        raise
    except PlacesError as exc:
        return SyncResult(dentist, "error", linked_place=linked, error=str(exc))

    result = SyncResult(dentist, "no_hours", business_status=business_status, linked_place=linked)
    if not hours:
        return result

    result.changes = {
        day: (getattr(dentist, day), value) for day, value in hours.items() if getattr(dentist, day) != value
    }
    if not result.changes:
        result.status = "unchanged"
        if not dry_run:
            Dentist.objects.filter(pk=dentist.pk).update(hours_synced_at=now)  # leaves updated_at alone
        return result

    result.status = "changed"
    if not dry_run:
        for day, (_, new_value) in result.changes.items():
            setattr(dentist, day, new_value)
        dentist.hours_synced_at = now
        # updated_at included so the sitemap lastmod reflects the change
        dentist.save(update_fields=[*result.changes, "hours_synced_at", "updated_at"])
    return result
