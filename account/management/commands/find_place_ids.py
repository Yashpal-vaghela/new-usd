"""
Bulk setup: find the Google Maps Place ID of every ACTIVE dentist that doesn't have one,
so you can review the matches before saving.

    python manage.py find_place_ids            # show matches only (nothing saved)
    python manage.py find_place_ids --save     # save the top match for each dentist
    python manage.py find_place_ids --id 12 --save   # (re)do a single active dentist

Always check the printed matches: text search can pick a different clinic with a
similar name. A wrong Place ID can be fixed by hand in Django admin.
(The nightly sync and the admin "Fetch hours" buttons also link missing Place IDs
automatically, using the top match.)
"""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from account.clinic_hours import active_dentists, build_search_query
from account.google_places import PlacesConfigError, PlacesError, search_places


class Command(BaseCommand):
    help = "Look up Google Maps Place IDs for active dentists that don't have one. Dry run unless --save."

    def add_arguments(self, parser):
        parser.add_argument("--save", action="store_true", help="Save the top match to google_place_id.")
        parser.add_argument("--id", type=int, help="Only this active Dentist id (re-looks it up even if it already has a Place ID).")

    def handle(self, *args, **opts):
        dentists = active_dentists()
        if opts["id"]:
            dentists = dentists.filter(pk=opts["id"])
            if not dentists:
                raise CommandError(f"Dentist {opts['id']} not found or not active (status off).")
        else:
            dentists = dentists.filter(Q(google_place_id__isnull=True) | Q(google_place_id=""))

        if not dentists:
            self.stdout.write("Nothing to do: every active dentist already has a Place ID.")
            return

        saved = not_found = failed = 0
        for dentist in dentists:
            query = build_search_query(dentist)
            self.stdout.write(f"\n[{dentist.id}] {dentist.clinic_name or dentist.name}\n    query: {query}")
            try:
                places = search_places(query, dentist.lat, dentist.long)
            except PlacesConfigError as exc:
                raise CommandError(f"Google Places API not usable, stopping: {exc}")
            except PlacesError as exc:
                failed += 1
                self.stderr.write(f"    ERROR: {exc}")
                continue

            if not places:
                not_found += 1
                self.stdout.write(self.style.WARNING("    no match on Google Maps"))
                continue

            for n, place in enumerate(places, 1):
                name = (place.get("displayName") or {}).get("text", "?")
                self.stdout.write(f"    {n}. {name} | {place.get('formattedAddress', '')}\n       {place['id']}")

            if opts["save"]:
                dentist.google_place_id = places[0]["id"]
                dentist.save(update_fields=["google_place_id"])
                saved += 1
                self.stdout.write(self.style.SUCCESS("    saved match 1"))

        summary = f"\nDone. {len(dentists)} looked up, {saved} saved, {not_found} not found, {failed} errors."
        if not opts["save"]:
            summary += " (dry run: re-run with --save to store the top matches)"
        self.stdout.write(summary)
