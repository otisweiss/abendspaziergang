"""Sammelt Kandidaten-Orte in Köln aus OpenStreetMap (Overpass API).

Die Orte landen mit Status „recherchiert“ in der Datenbank und sind nicht öffentlich.
Übernommen werden nur institutionelle Angaben. Daten: © OpenStreetMap-Mitwirkende, ODbL.

    python manage.py import_osm                 # live von der Overpass API
    python manage.py import_osm --file daten.json   # gespeicherte Overpass-Antwort
    python manage.py import_osm --dry-run
"""

import json
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand, CommandError

from venues.koeln import district_for_quarter
from venues.models import Venue

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Kategorien, die typischerweise Räume für Gruppen haben
FILTERS = [
    '["amenity"="community_centre"]',
    '["amenity"="social_centre"]',
    '["amenity"="social_facility"]["social_facility"="outreach"]',
    '["amenity"="arts_centre"]',
    '["amenity"="library"]',
    '["amenity"="events_venue"]',
    '["amenity"="youth_centre"]',
    '["community_centre"]',
    '["club"]["name"]',
    '["leisure"="hackerspace"]',
]

OPERATOR_TYPES = {
    "public": Venue.OperatorType.PUBLIC,
    "government": Venue.OperatorType.PUBLIC,
    "municipal": Venue.OperatorType.PUBLIC,
    "religious": Venue.OperatorType.CHURCH,
    "community": Venue.OperatorType.NONPROFIT,
    "ngo": Venue.OperatorType.NONPROFIT,
    "non_profit": Venue.OperatorType.NONPROFIT,
    "private": Venue.OperatorType.BUSINESS,
}


def build_query():
    parts = "\n".join(f"  nwr{f}(area.koeln);" for f in FILTERS)
    return (
        '[out:json][timeout:120];\n'
        'area["name"="Köln"]["boundary"="administrative"]["admin_level"="6"]->.koeln;\n'
        f"(\n{parts}\n);\nout center tags;"
    )


def guess_operator_type(tags):
    if (t := OPERATOR_TYPES.get(tags.get("operator:type", ""))) is not None:
        return t
    text = (tags.get("operator", "") + " " + tags.get("name", "")).lower()
    if any(w in text for w in ["pfarr", "kirche", "gemeinde st", "evangel", "kathol", "moschee", "synagog"]):
        return Venue.OperatorType.CHURCH
    if "stadt köln" in text or tags.get("amenity") == "library" and "stadtbibliothek" in text:
        return Venue.OperatorType.PUBLIC
    if "e.v." in text or "verein" in text:
        return Venue.OperatorType.NONPROFIT
    return ""


class Command(BaseCommand):
    help = "Importiert Kandidaten-Orte aus OpenStreetMap (Status: recherchiert)."

    def add_arguments(self, parser):
        parser.add_argument("--file", help="Gespeicherte Overpass-JSON-Antwort statt Live-Abfrage")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--print-query", action="store_true", help="Nur die Overpass-Abfrage ausgeben")

    def handle(self, *args, **opts):
        query = build_query()
        if opts["print_query"]:
            self.stdout.write(query)
            return
        if opts["file"]:
            with open(opts["file"], encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            body = urllib.parse.urlencode({"data": query}).encode()
            req = urllib.request.Request(OVERPASS_URL, data=body, headers={"User-Agent": "Veedelsraeume-Import/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.load(resp)
            except OSError as exc:
                raise CommandError(f"Overpass nicht erreichbar: {exc}") from exc

        created = skipped = 0
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            name = tags.get("name")
            if not name:
                skipped += 1
                continue
            osm_id = f"{el['type']}/{el['id']}"
            if Venue.objects.filter(osm_id=osm_id).exists():
                skipped += 1
                continue
            street = " ".join(p for p in [tags.get("addr:street", ""), tags.get("addr:housenumber", "")] if p)
            # Bereits abgelehnte Orte (Sperrvermerk) nicht erneut aufnehmen
            if street and Venue.objects.filter(status=Venue.Status.REJECTED, name__iexact=name, street__iexact=street).exists():
                skipped += 1
                continue
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            quarter = tags.get("addr:suburb", "")
            venue = Venue(
                name=name[:200],
                operator=tags.get("operator", "")[:200],
                operator_type=guess_operator_type(tags),
                website=(tags.get("website") or tags.get("contact:website") or "")[:200],
                street=street[:200],
                postcode=tags.get("addr:postcode", "")[:5],
                quarter=quarter[:80],
                district=district_for_quarter(quarter),
                latitude=round(lat, 6) if lat else None,
                longitude=round(lon, 6) if lon else None,
                step_free=tags.get("wheelchair") == "yes",
                accessible_wc=tags.get("toilets:wheelchair") == "yes",
                # Nur Funktionsadressen aus OSM; Telefonnummern bewusst nicht übernommen
                contact_email=(tags.get("email") or tags.get("contact:email") or "")[:254],
                status=Venue.Status.RESEARCHED,
                source=Venue.Source.OSM,
                source_reference=f"https://www.openstreetmap.org/{osm_id} (© OpenStreetMap-Mitwirkende, ODbL)",
                osm_id=osm_id,
                internal_notes=f"OSM-Kategorie: {tags.get('amenity') or tags.get('club') or tags.get('leisure') or '?'}",
            )
            created += 1
            if not opts["dry_run"]:
                venue.save()
        self.stdout.write(self.style.SUCCESS(f"{created} neue Orte, {skipped} übersprungen{' (Probelauf)' if opts['dry_run'] else ''}."))
