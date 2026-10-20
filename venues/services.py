import copy
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.base import ModelState
from django.template.loader import render_to_string
from django.utils import timezone

from .models import ListingRequest, Venue


class ListingRequestError(Exception):
    pass


def send_templated_mail(template, to, context):
    context = {"SITE_NAME": settings.SITE_NAME, "SITE_URL": settings.SITE_URL, "OPERATOR_NAME": settings.OPERATOR_NAME, **context}
    subject = render_to_string(f"emails/{template}_subject.txt", context).strip()
    body = render_to_string(f"emails/{template}.txt", context)
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to])


def notify_moderation(subject, text):
    """Kurzer Hinweis an den Betreiberverein. Enthält bewusst keine Inhalte, nur einen Link zur Verwaltung."""
    if settings.MODERATION_EMAILS:
        body = f"{text}\n\nZur Verwaltung: {settings.SITE_URL}/verwaltung/\n"
        send_mail(f"[{settings.SITE_NAME}] {subject}", body, settings.DEFAULT_FROM_EMAIL, settings.MODERATION_EMAILS)


def send_listing_request(venue, sent_by=None):
    """Schickt einem recherchierten Ort die Anfrage, ob er gelistet werden möchte."""
    if venue.status not in (Venue.Status.RESEARCHED, Venue.Status.REQUESTED, Venue.Status.PUBLIC_SOURCE):
        raise ListingRequestError(f"„{venue}“ hat den Status „{venue.get_status_display()}“.")
    recipient = venue.manager_email or venue.contact_email
    if not recipient:
        raise ListingRequestError(f"Für „{venue}“ ist keine E-Mail-Adresse hinterlegt.")
    if venue.listing_request_count >= settings.MAX_LISTING_REQUESTS:
        raise ListingRequestError(f"„{venue}“ wurde bereits {venue.listing_request_count}-mal angefragt.")

    days = settings.RETENTION["listing_request_validity"]
    token = venue.issue_edit_token(valid_days=days)
    is_reminder = venue.listing_request_count > 0
    send_templated_mail(
        "listing_request",
        recipient,
        {"venue": venue, "url": venue.edit_url(token), "days": days, "is_reminder": is_reminder},
    )
    # Eine frühere Anfrage ist mit dem neuen Link ungültig geworden.
    venue.listing_requests.filter(outcome=ListingRequest.Outcome.OPEN).update(outcome=ListingRequest.Outcome.EXPIRED)
    ListingRequest.objects.create(
        venue=venue, recipient=recipient, sent_by=sent_by, expires_at=timezone.now() + timedelta(days=days)
    )
    venue.listing_request_count += 1
    if venue.status != Venue.Status.PUBLIC_SOURCE:
        # Orte aus öffentlicher Quelle bleiben während der Anfrage sichtbar.
        venue.status = Venue.Status.REQUESTED
    if not venue.manager_email:
        venue.manager_email = recipient
    venue.save(update_fields=["listing_request_count", "status", "manager_email", "updated_at"])


def close_open_requests(venue, outcome):
    venue.listing_requests.filter(outcome=ListingRequest.Outcome.OPEN).update(
        outcome=outcome, answered_at=timezone.now()
    )


def send_submission_confirmation(venue):
    """Double-Opt-in für über das Formular gemeldete Orte."""
    days = settings.RETENTION["unconfirmed_submissions"]
    token = venue.issue_edit_token(valid_days=days)
    send_templated_mail("submission_confirm", venue.manager_email, {"venue": venue, "url": venue.edit_url(token), "days": days})


def send_new_edit_link(venue):
    # Vor der Zustimmung bleibt der Link befristet, danach gilt er dauerhaft.
    days = None if venue.consent_at else settings.RETENTION["listing_request_validity"]
    token = venue.issue_edit_token(valid_days=days)
    send_templated_mail("edit_link", venue.manager_email, {"venue": venue, "url": venue.edit_url(token)})


# --- Aktualitätsabfrage --------------------------------------------------------


def run_freshness_checks(now=None):
    """Fragt regelmäßig nach, ob gelistete Angebote noch stimmen. Täglich ausführen.

    Ablauf je Ort: Abfrage → nach FRESHNESS_REMINDER_DAYS eine Erinnerung → nach
    FRESHNESS_PAUSE_DAYS ohne Antwort wird der Eintrag pausiert (nicht gelöscht).
    Gibt die Zahl der gesendeten Abfragen, Erinnerungen und Pausierungen zurück.
    """
    now = now or timezone.now()
    interval = timedelta(days=settings.FRESHNESS_INTERVAL_DAYS)
    reminder_after = timedelta(days=settings.FRESHNESS_REMINDER_DAYS)
    pause_after = timedelta(days=settings.FRESHNESS_PAUSE_DAYS)
    counts = {"abfragen": 0, "erinnerungen": 0, "pausiert": 0}
    weeks = {
        "reminder_weeks": settings.FRESHNESS_REMINDER_DAYS // 7,
        "pause_weeks": settings.FRESHNESS_PAUSE_DAYS // 7,
        "remaining_weeks": max(1, (settings.FRESHNESS_PAUSE_DAYS - settings.FRESHNESS_REMINDER_DAYS) // 7),
    }

    for venue in Venue.objects.confirmed().exclude(manager_email=""):
        confirmed = venue.needs_freshness_check_since()
        check = venue.freshness_check_sent_at
        open_check = check is not None and check > confirmed

        if not open_check:
            if confirmed < now - interval:
                token = venue.issue_edit_token()
                send_templated_mail("freshness_check", venue.manager_email, {"venue": venue, "url": venue.edit_url(token), **weeks})
                venue.freshness_check_sent_at = now
                venue.freshness_reminder_sent_at = None
                venue.save(update_fields=["freshness_check_sent_at", "freshness_reminder_sent_at", "updated_at"])
                counts["abfragen"] += 1
            continue

        if check < now - pause_after:
            token = venue.issue_edit_token()
            venue.status = Venue.Status.PAUSED
            venue.paused_reason = "Keine Antwort auf die Aktualitätsabfrage"
            venue.save(update_fields=["status", "paused_reason", "updated_at"])
            send_templated_mail("freshness_paused", venue.manager_email, {"venue": venue, "url": venue.edit_url(token)})
            counts["pausiert"] += 1
        elif check < now - reminder_after and venue.freshness_reminder_sent_at is None:
            token = venue.issue_edit_token()
            send_templated_mail("freshness_reminder", venue.manager_email, {"venue": venue, "url": venue.edit_url(token), **weeks})
            venue.freshness_reminder_sent_at = now
            venue.save(update_fields=["freshness_reminder_sent_at", "updated_at"])
            counts["erinnerungen"] += 1
    return counts


def confirm_still_current(venue):
    venue.last_confirmed_at = timezone.now()
    venue.freshness_check_sent_at = None
    venue.freshness_reminder_sent_at = None
    venue.paused_reason = ""
    venue.save(update_fields=["last_confirmed_at", "freshness_check_sent_at", "freshness_reminder_sent_at", "paused_reason", "updated_at"])


# --- Nutzungsanfragen an nicht öffentliche Orte -------------------------------


def create_usage_request(form, venue, user, batch=""):
    request_obj = form.save(commit=False)
    if batch:
        # Für jeden Ort ein eigenes Objekt aus denselben Formulardaten
        request_obj = copy.copy(request_obj)
        request_obj._state = ModelState()
        request_obj.pk = None
        request_obj.room = None
    request_obj.batch = batch
    request_obj.venue = venue
    request_obj.user = user
    request_obj.expires_at = timezone.now() + timedelta(days=settings.USAGE_REQUEST_VALIDITY_DAYS)
    token = request_obj.issue_token()
    request_obj.save()
    send_templated_mail(
        "usage_request",
        venue.manager_email,
        {
            "venue": venue,
            "req": request_obj,
            "group": getattr(user, "group_profile", None),
            "url": request_obj.respond_url(token),
            "days": settings.USAGE_REQUEST_VALIDITY_DAYS,
        },
    )
    return request_obj


def answer_usage_request(request_obj, accept, note=""):
    from .models import UsageRequest

    request_obj.status = UsageRequest.Status.ACCEPTED if accept else UsageRequest.Status.DECLINED
    request_obj.response_note = note[:500]
    request_obj.answered_at = timezone.now()
    request_obj.token_hash = ""
    request_obj.save()
    template = "usage_accepted" if accept else "usage_declined"
    send_templated_mail(
        template,
        request_obj.reply_email,
        {"req": request_obj, "venue": request_obj.venue, "url": settings.SITE_URL + request_obj.venue.get_absolute_url()},
    )
    # Eine Antwort zählt auch als Lebenszeichen des Raumgebers.
    confirm_still_current(request_obj.venue)


def create_batch_request(form, venues, user):
    """Schickt dieselbe Anfrage an mehrere nicht öffentliche Orte. Jeder Raumgeber sieht nur seine eigene."""
    batch = secrets.token_hex(8)
    created = [create_usage_request(form, venue, user, batch=batch) for venue in venues]
    return batch, created
