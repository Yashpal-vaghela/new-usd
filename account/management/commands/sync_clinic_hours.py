"""
Nightly job: copy each ACTIVE dentist's weekly opening hours from Google Maps into Mon–Sun.

    python manage.py sync_clinic_hours             # every active dentist (status=True)
    python manage.py sync_clinic_hours --dry-run   # show what would change, save nothing
    python manage.py sync_clinic_hours --id 12     # a single (active) dentist

Active dentists without a Place ID are linked to their best Google Maps match first.
The same sync can be run from Django admin: Dentists -> "Fetch Google hours (all active)".

One Google call per dentist (Place Details Enterprise SKU), e.g. 54 dentists once a
night = ~1,700 calls/month, inside the 7,000 free calls/month on India pricing.
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from account.clinic_hours import DAY_ORDER, active_dentists, sync_dentist_hours
from account.google_places import PlacesConfigError


class Command(BaseCommand):
    help = "Update active dentists' Mon–Sun opening hours from Google Maps."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show changes without saving.")
        parser.add_argument("--id", type=int, help="Only this Dentist id (must be active).")

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]
        dentists = active_dentists()
        if opts["id"]:
            dentists = dentists.filter(pk=opts["id"])
            if not dentists:
                raise CommandError(f"Dentist {opts['id']} not found or not active (status off).")

        now = timezone.now()
        self.stdout.write(f"[{timezone.localtime(now):%Y-%m-%d %H:%M}] Syncing hours for {len(dentists)} active dentists"
                          + (" (dry run)" if dry_run else ""))

        counts = {}
        for dentist in dentists:
            try:
                result = sync_dentist_hours(dentist, now=now, dry_run=dry_run)
            except PlacesConfigError as exc:
                raise CommandError(f"Google Places API not usable, stopping: {exc}")
            counts[result.status] = counts.get(result.status, 0) + 1
            label = f"[{dentist.id}] {result.label}"

            if result.linked_place:
                self.stdout.write(f"{label}: linked to Google place {result.linked_place_text}")
            if result.business_status and result.business_status != "OPERATIONAL":
                self.stdout.write(self.style.WARNING(f"{label}: Google says {result.business_status}"))

            if result.status == "changed":
                self.stdout.write(self.style.SUCCESS(f"{label}: hours changed"))
                for day in DAY_ORDER:
                    if day in result.changes:
                        old, new = result.changes[day]
                        self.stdout.write(f"    {day}: {old!r} -> {new!r}")
            elif result.status == "no_hours":
                self.stdout.write(self.style.WARNING(f"{label}: no opening hours on Google, kept existing values"))
            elif result.status == "not_found":
                self.stdout.write(self.style.WARNING(f"{label}: not found on Google Maps, add the Place ID in admin"))
            elif result.status == "error":
                self.stderr.write(f"{label}: ERROR {result.error}")

        self.stdout.write("Done. " + " | ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
