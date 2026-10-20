import copy
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.db import transaction
from django.db.models.base import ModelState
from django.template.loader import render_to_string
from django.utils import timezone

from .models import ListingRequest, Venue


class ListingRequestError(Exception):
    pass


def send_templated_mail(template, to, context, reply_to=None, from_email=None):
    context = {"SITE_NAME": settings.SITE_NAME, "SITE_URL": settings.SITE_URL, "OPERATOR_NAME": settings.OPERATOR_NAME, **context}
    subject = render_to_string(f"emails/{template}_subject.txt", context).strip()
    body = render_to_string(f"emails/{template}.txt", context)
    EmailMessage(
        subject, body, from_email or settings.DEFAULT_FROM_EMAIL, [to], reply_to=[reply_to] if reply_to else None
    ).send()


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


# --- Raumanfragen über die zentrale Anfrage-Adresse -----------------------------
#
# Alle Anfragen gehen von settings.REQUEST_FROM_EMAIL raus. Reply-To ist die Antwort-Adresse
# der Gruppe, der Raumgeber kann also einfach auf „Antworten“ klicken. Pro Gruppe läuft für
# einen Termin immer nur eine Anfrage (siehe RequestBaseForm). Reihenanfragen fragen die Orte
# nacheinander an: Erst nach einer Absage, einem Rückzug oder Ablauf kommt der nächste dran.


def _request_mail(template, to, context, reply_to=None):
    send_templated_mail(template, to, context, reply_to=reply_to, from_email=settings.REQUEST_FROM_EMAIL)


def _activate(request_obj):
    """Schickt eine (eingereihte oder neue) Anfrage an den Raumgeber."""
    from .models import UsageRequest

    venue = request_obj.venue
    request_obj.status = UsageRequest.Status.OPEN
    request_obj.expires_at = timezone.now() + timedelta(days=settings.USAGE_REQUEST_VALIDITY_DAYS)
    token = request_obj.issue_token()
    request_obj.save()
    _request_mail(
        "usage_request",
        venue.request_recipient,
        {
            "venue": venue,
            "req": request_obj,
            "group": getattr(request_obj.user, "group_profile", None),
            "url": request_obj.respond_url(token),
            "days": settings.USAGE_REQUEST_VALIDITY_DAYS,
        },
        reply_to=request_obj.reply_email,
    )


def _copy_request(request_obj):
    clone = copy.copy(request_obj)
    clone._state = ModelState()
    clone.pk = None
    return clone


def create_usage_request(form, venue, user):
    request_obj = form.save(commit=False)
    request_obj.venue = venue
    request_obj.user = user
    with transaction.atomic():
        _activate(request_obj)
    return request_obj


def create_series_request(form, venues, user):
    """Reihenanfrage: der erste Ort wird sofort angefragt, die übrigen werden eingereiht."""
    from .models import UsageRequest

    batch = secrets.token_hex(8)
    template = form.save(commit=False)
    created = []
    with transaction.atomic():
        for position, venue in enumerate(venues, start=1):
            item = _copy_request(template)
            item.venue, item.user, item.room = venue, user, None
            item.batch, item.queue_position = batch, position
            if position == 1:
                _activate(item)
            else:
                item.status = UsageRequest.Status.QUEUED
                item.token_hash = ""
                item.save()
            created.append(item)
    return batch, created


def advance_series(request_obj):
    """Nach einer Absage, einem Rückzug oder Ablauf: nächsten Ort der Reihe anfragen."""
    from .models import UsageRequest

    if not request_obj.batch:
        return None
    nxt = (
        UsageRequest.objects.filter(batch=request_obj.batch, status=UsageRequest.Status.QUEUED)
        .order_by("queue_position")
        .select_related("venue", "user")
        .first()
    )
    if nxt is None:
        if not UsageRequest.objects.filter(batch=request_obj.batch, status=UsageRequest.Status.ACCEPTED).exists():
            _request_mail("series_exhausted", request_obj.reply_email, {"req": request_obj})
        return None
    if not nxt.venue.accepts_platform_requests:
        nxt.status = UsageRequest.Status.CANCELLED
        nxt.save(update_fields=["status"])
        return advance_series(nxt)
    _activate(nxt)
    _request_mail("series_next", nxt.reply_email, {"req": nxt, "previous": request_obj})
    return nxt


def cancel_rest_of_series(request_obj):
    from .models import UsageRequest

    if request_obj.batch:
        UsageRequest.objects.filter(batch=request_obj.batch, status=UsageRequest.Status.QUEUED).update(
            status=UsageRequest.Status.CANCELLED
        )


def answer_usage_request(request_obj, accept, note=""):
    """Antwort des Raumgebers über den Link aus der E-Mail."""
    from .models import UsageRequest

    request_obj.status = UsageRequest.Status.ACCEPTED if accept else UsageRequest.Status.DECLINED
    request_obj.confirmed_by_host = accept
    request_obj.response_note = note[:500]
    request_obj.answered_at = timezone.now()
    request_obj.token_hash = ""
    request_obj.save()
    venue = request_obj.venue
    template = "usage_accepted" if accept else "usage_declined"
    # Bei einer Zusage antwortet die Gruppe direkt an den Kontakt des Ortes.
    _request_mail(
        template,
        request_obj.reply_email,
        {"req": request_obj, "venue": venue, "url": settings.SITE_URL + venue.get_absolute_url()},
        reply_to=venue.contact_email if accept and venue.contact_email else None,
    )
    if accept:
        cancel_rest_of_series(request_obj)
    else:
        advance_series(request_obj)
    # Eine Antwort zählt auch als Lebenszeichen des Raumgebers.
    if venue.status == Venue.Status.LISTED:
        confirm_still_current(venue)


def mark_outcome_by_group(request_obj, outcome):
    """Die Gruppe hat direkt per E-Mail eine Antwort bekommen und trägt sie ein.

    Eine so eingetragene Zusage schaltet bei nicht öffentlichen Orten keine Details frei.
    """
    from .models import UsageRequest

    request_obj.answered_at = timezone.now()
    request_obj.token_hash = ""
    if outcome == "zugesagt":
        request_obj.status = UsageRequest.Status.ACCEPTED
        request_obj.save()
        cancel_rest_of_series(request_obj)
    else:
        request_obj.status = UsageRequest.Status.DECLINED
        request_obj.save()
        advance_series(request_obj)


def withdraw_usage_request(request_obj):
    """Gruppe zieht eine Anfrage zurück. Bei einer offenen Reihe kommt der nächste Ort dran."""
    from .models import UsageRequest

    previous = request_obj.status
    request_obj.status = UsageRequest.Status.WITHDRAWN if previous != UsageRequest.Status.QUEUED else UsageRequest.Status.CANCELLED
    request_obj.token_hash = ""
    request_obj.save(update_fields=["status", "token_hash"])
    if previous in (UsageRequest.Status.OPEN, UsageRequest.Status.ACCEPTED):
        _request_mail(
            "usage_withdrawn", request_obj.venue.request_recipient, {"req": request_obj, "venue": request_obj.venue},
            reply_to=request_obj.reply_email,
        )
    if previous == UsageRequest.Status.OPEN:
        advance_series(request_obj)


def end_series(request_obj):
    """Ganze Reihe beenden: offene Anfrage zurückziehen, eingereihte streichen."""
    from .models import UsageRequest

    cancel_rest_of_series(request_obj)
    current = UsageRequest.objects.filter(batch=request_obj.batch, status=UsageRequest.Status.OPEN).first()
    if current:
        withdraw_usage_request(current)


def expire_usage_requests(now=None):
    """Unbeantwortete Anfragen beenden, Gruppe informieren, Reihe fortsetzen. Täglich ausführen."""
    from .models import UsageRequest

    now = now or timezone.now()
    count = 0
    for item in UsageRequest.objects.filter(status=UsageRequest.Status.OPEN, expires_at__lt=now).select_related("venue", "user"):
        item.status = UsageRequest.Status.EXPIRED
        item.token_hash = ""
        item.save(update_fields=["status", "token_hash"])
        if item.batch:
            advance_series(item)  # informiert die Gruppe über den nächsten Ort oder das Ende der Reihe
        else:
            _request_mail("usage_expired", item.reply_email, {"req": item, "venue": item.venue})
        count += 1
    return count
