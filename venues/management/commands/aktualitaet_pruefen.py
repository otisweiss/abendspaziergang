"""Fragt bei gelisteten Orten regelmäßig per E-Mail nach, ob das Angebot noch aktuell ist.
Täglich ausführen (Docker-Dienst „cron“).

    python manage.py aktualitaet_pruefen
"""

from django.core.management.base import BaseCommand

from venues.services import run_freshness_checks


class Command(BaseCommand):
    help = "Sendet Aktualitätsabfragen und Erinnerungen, pausiert Einträge ohne Antwort."

    def handle(self, **opts):
        counts = run_freshness_checks()
        self.stdout.write(self.style.SUCCESS(", ".join(f"{k}: {v}" for k, v in counts.items())))
