from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import ListingRequest, Venue


class ListingRequestError(Exception):
    pass


def send_templated_mail(template, to, context):
    context = {"SITE_NAME": settings.SITE_NAME, "SITE_URL": settings.SITE_URL, **context}
    subject = render_to_string(f"emails/{template}_subject.txt", context).strip()
    body = render_to_string(f"emails/{template}.txt", context)
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to])


def send_listing_request(venue, sent_by=None):
    """Schickt einem recherchierten Ort die Anfrage, ob er gelistet werden möchte."""
    if venue.status not in (Venue.Status.RESEARCHED, Venue.Status.REQUESTED):
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
