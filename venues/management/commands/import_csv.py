"""Importiert Orte aus einer CSV-Datei (Handrecherche). Vorlage: docs/vorlage-recherche.csv

    python manage.py import_csv recherche.csv [--dry-run]

Spalten (Kopfzeile, Trennzeichen ; oder ,): name, operator, operator_type, street, postcode,
quarter, website, contact_email, contact_url, source_reference, latitude, longitude, notes
"""

import csv
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from venues.models import Venue


def _decimal(value):
    try:
        return Decimal(value.replace(",", ".")) if value else None
    except InvalidOperation:
        return None


class Command(BaseCommand):
    help = "Importiert recherchierte Orte aus CSV (Status: recherchiert)."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, path, dry_run=False, **opts):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            sample = fh.read(4096)
            fh.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=";,")
            rows = list(csv.DictReader(fh, dialect=dialect))
        if not rows or "name" not in rows[0]:
            raise CommandError("CSV braucht mindestens die Spalte „name“.")
        valid_types = set(Venue.OperatorType.values)
        created = skipped = 0
        for row in rows:
            row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
            if not row.get("name"):
                skipped += 1
                continue
            if Venue.objects.filter(name__iexact=row["name"], street__iexact=row.get("street", "")).exists():
                skipped += 1
                continue
            venue = Venue(
                name=row["name"],
                operator=row.get("operator", ""),
                operator_type=row.get("operator_type", "") if row.get("operator_type") in valid_types else "",
                street=row.get("street", ""),
                postcode=row.get("postcode", "")[:5],
                quarter=row.get("quarter", ""),
                website=row.get("website", ""),
                contact_email=row.get("contact_email", ""),
                contact_url=row.get("contact_url", ""),
                source_reference=row.get("source_reference", ""),
                latitude=_decimal(row.get("latitude", "")),
                longitude=_decimal(row.get("longitude", "")),
                internal_notes=row.get("notes", ""),
                status=Venue.Status.RESEARCHED,
                source=Venue.Source.CSV,
            )
            created += 1
            if not dry_run:
                venue.save()
        self.stdout.write(self.style.SUCCESS(f"{created} neue Orte, {skipped} übersprungen."))
