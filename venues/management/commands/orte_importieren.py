"""Importiert recherchierte Orte mit Räumen aus einer JSON-Datei, z. B. data/orte_koeln.json.

    python manage.py orte_importieren data/orte_koeln.json [--dry-run]

Status „quelle“ macht einen Ort sofort sichtbar, mit dem Hinweis „noch nicht vom Ort bestätigt“.
Das ist nur für Einrichtungen erlaubt, die selbst öffentlich Räume anbieten (siehe Venue.clean).
Vorhandene Orte (gleicher Name und gleiche Straße) und Orte mit Sperrvermerk werden übersprungen.
"""

import json

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from venues.models import Equipment, Purpose, Room, TimeSlot, Venue

VENUE_FIELDS = [
    "name", "operator", "operator_type", "description", "website", "street", "postcode", "quarter", "district",
    "transit", "step_free", "elevator", "accessible_wc", "hearing_loop", "disabled_parking", "accessibility_notes",
    "contact_email", "contact_phone", "contact_url", "contact_notes", "source_reference",
]
STATUS = {"quelle": Venue.Status.PUBLIC_SOURCE, "recherchiert": Venue.Status.RESEARCHED}


class Command(BaseCommand):
    help = "Importiert Orte und Räume aus JSON (Status: quelle oder recherchiert)."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, path, dry_run=False, **opts):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        created = skipped = 0
        for entry in data.get("orte", []):
            if Venue.objects.filter(name__iexact=entry["name"], street__iexact=entry.get("street", "")).exists():
                skipped += 1
                continue
            status = STATUS.get(entry.get("status", "recherchiert"))
            if status is None:
                raise CommandError(f"Unbekannter Status bei „{entry['name']}“")
            venue = Venue(
                status=status, source=Venue.Source.RESEARCH, **{k: entry[k] for k in VENUE_FIELDS if k in entry}
            )
            try:
                venue.clean()
            except ValidationError as exc:
                self.stderr.write(f"Übersprungen: {entry['name']}: {exc.messages[0]}")
                skipped += 1
                continue
            created += 1
            if dry_run:
                continue
            with transaction.atomic():
                venue.save()
                for r in entry.get("rooms", []):
                    room = Room.objects.create(
                        venue=venue, name=r["name"], capacity=r.get("capacity"), area_sqm=r.get("area_sqm"),
                        cost=r.get("cost", Room.Cost.ON_REQUEST), price_notes=r.get("price_notes", ""),
                    )
                    TimeSlot.objects.bulk_create([TimeSlot(room=room, day=day, period=period) for day, period in r.get("slots", [])])
                    room.equipment.set(Equipment.objects.filter(slug__in=r.get("equipment", [])))
                    room.purposes.set(Purpose.objects.filter(slug__in=r.get("purposes", [])))
        self.stdout.write(self.style.SUCCESS(f"{created} Orte importiert, {skipped} übersprungen."))
