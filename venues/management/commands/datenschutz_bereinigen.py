"""Setzt die Löschfristen um. Täglich ausführen (Cron oder Docker-Dienst „cron“).

    python manage.py datenschutz_bereinigen [--dry-run]
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from venues.models import ListingRequest, UsageRequest, Venue
from venues.services import send_templated_mail


class Command(BaseCommand):
    help = "Löscht abgelaufene und nicht mehr benötigte personenbezogene Daten."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, dry_run=False, **opts):
        now = timezone.now()
        r = settings.RETENTION
        User = get_user_model()
        report = []

        unverified = User.objects.filter(
            is_active=False, is_staff=False, last_login__isnull=True,
            date_joined__lt=now - timedelta(days=r["unverified_accounts"]),
        )
        report.append(("Unbestätigte Konten", unverified))

        inactive = User.objects.filter(is_staff=False).filter(
            Q(last_login__lt=now - timedelta(days=r["inactive_accounts"]))
            | Q(last_login__isnull=True, is_active=True, date_joined__lt=now - timedelta(days=r["inactive_accounts"]))
        )
        report.append(("Konten ohne Anmeldung seit Frist", inactive))

        unconfirmed = Venue.objects.filter(
            status=Venue.Status.UNCONFIRMED, created_at__lt=now - timedelta(days=r["unconfirmed_submissions"])
        )
        report.append(("Unbestätigte Meldungen", unconfirmed))

        for label, qs in report:
            n = qs.count()
            self.stdout.write(f"{label}: {n}")
            if n and not dry_run:
                qs.delete()

        # Abgelaufene Listungsanfragen: zurück auf „recherchiert“, Link ungültig machen
        expired = ListingRequest.objects.filter(outcome=ListingRequest.Outcome.OPEN, expires_at__lt=now)
        venue_ids = list(expired.values_list("venue_id", flat=True))
        self.stdout.write(f"Abgelaufene Listungsanfragen: {len(venue_ids)}")
        if venue_ids and not dry_run:
            expired.update(outcome=ListingRequest.Outcome.EXPIRED)
            Venue.objects.filter(pk__in=venue_ids, status=Venue.Status.REQUESTED).update(
                status=Venue.Status.RESEARCHED, edit_token_hash="", edit_token_expires_at=None
            )

        # Unbeantwortete Nutzungsanfragen: Gruppe informieren, Link ungültig machen
        expired_usage = UsageRequest.objects.filter(status=UsageRequest.Status.OPEN, expires_at__lt=now).select_related("venue")
        self.stdout.write(f"Abgelaufene Nutzungsanfragen: {expired_usage.count()}")
        if not dry_run:
            for item in expired_usage:
                item.status = UsageRequest.Status.EXPIRED
                item.token_hash = ""
                item.save(update_fields=["status", "token_hash"])
                send_templated_mail("usage_expired", item.reply_email, {"req": item, "venue": item.venue})

        # Alte Nutzungsanfragen löschen. Damit endet auch ein gewährter Zugang zu den Details.
        old_usage = UsageRequest.objects.filter(created_at__lt=now - timedelta(days=settings.USAGE_REQUEST_RETENTION_DAYS))
        self.stdout.write(f"Alte Nutzungsanfragen: {old_usage.count()}")
        if not dry_run:
            old_usage.delete()

        # Abgelaufene Bearbeitungslinks entfernen
        tokens = Venue.objects.filter(edit_token_expires_at__lt=now).exclude(edit_token_hash="")
        self.stdout.write(f"Abgelaufene Bearbeitungslinks: {tokens.count()}")
        if not dry_run:
            tokens.update(edit_token_hash="", edit_token_expires_at=None)
            Session.objects.filter(expire_date__lt=now).delete()

        self.stdout.write(self.style.SUCCESS("Fertig." + (" (Probelauf, nichts gelöscht)" if dry_run else "")))
