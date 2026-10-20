from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.conf import settings

from .forms import (
    ConsentForm, RequestLinkForm, RespondForm, RoomFormSet, SearchForm, SeriesRequestForm, SubmissionForm, UsageRequestForm,
    VenueForm,
)
from .koeln import ALL_QUARTERS, DISTRICTS
from .models import Bookmark, ListingRequest, UsageRequest, Venue
from .ratelimit import is_limited
from .search import search_venues
from .services import (
    answer_usage_request, close_open_requests, confirm_still_current, create_series_request, create_usage_request,
    end_series, mark_outcome_by_group, notify_moderation, withdraw_usage_request,
    send_new_edit_link, send_submission_confirmation,
)


def group_required(view):
    """Suche und Details nur für freigeschaltete Gruppen (und die Redaktion)."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.can_search:
            return render(request, "accounts/pending.html", status=403)
        return view(request, *args, **kwargs)

    return wrapper


# --- Öffentliche Seiten -------------------------------------------------------


def home(request):
    listed = Venue.objects.listed()
    by_district = dict(listed.values_list("district").annotate(n=Count("id")))
    districts = [(label, by_district.get(key, 0)) for key, label in DISTRICTS]
    context = {
        "listed_count": listed.count(),
        "confirmed_count": Venue.objects.confirmed().count(),
        "collected_count": Venue.objects.exclude(status=Venue.Status.REJECTED).count(),
        "districts": districts,
    }
    return render(request, "pages/home.html", context)


# --- Suche für Gruppen --------------------------------------------------------


@group_required
def search(request):
    form = SearchForm(request.GET or None)
    data = form.cleaned_data if form.is_valid() else {}
    accessible = Venue.objects.accessible_ids(request.user)
    results = search_venues(data, accessible)
    page = Paginator(results, settings.SEARCH_PAGE_SIZE).get_page(request.GET.get("seite"))
    query = request.GET.copy()
    query.pop("seite", None)
    map_points = [
        {"lat": float(v.latitude), "lon": float(v.longitude), "name": v.name, "url": v.get_absolute_url()}
        for v in page
        # Nicht öffentliche Orte erscheinen nicht auf der Karte, bis die Gruppe Zugang hat.
        if v.has_location and (v.is_public or v.pk in accessible)
    ]
    bookmarked = set(request.user.bookmarks.values_list("venue_id", flat=True))
    series_count = 0
    if data.get("district") or data.get("quarter"):
        series_count = min(len(series_targets(data, accessible)), settings.MAX_SERIES_TARGETS)
    return render(
        request,
        "venues/search.html",
        {
            "form": form,
            "page": page,
            "total": page.paginator.count,
            "querystring": query.urlencode(),
            "map_points": map_points,
            "bookmarked": bookmarked,
            "accessible": accessible,
            "series_count": series_count,
            "location_chosen": bool(data.get("district") or data.get("quarter")),
        },
    )


@group_required
def detail(request, pk):
    venue = get_object_or_404(Venue.objects.prefetch_related("rooms__equipment", "rooms__purposes", "rooms__slots"), pk=pk)
    if not venue.is_visible and not request.user.is_staff:
        raise Http404
    has_access = venue.is_public or request.user.is_staff or pk in Venue.objects.accessible_ids(request.user)
    own_requests = venue.usage_requests.filter(user=request.user)
    open_request = own_requests.filter(status__in=[UsageRequest.Status.OPEN, UsageRequest.Status.QUEUED]).first()

    request_form = None
    if venue.accepts_platform_requests and open_request is None:
        initial = {"reply_email": request.user.email}
        request_form = UsageRequestForm(request.POST or None, venue=venue, user=request.user, initial=initial)
        if request.method == "POST":
            if is_limited(request, f"usage:{request.user.pk}", limit=settings.MAX_USAGE_REQUESTS_PER_DAY, window_seconds=86400):
                messages.error(request, "Ihr habt heute schon viele Anfragen geschickt. Bitte versucht es morgen wieder.")
            elif request_form.is_valid():
                create_usage_request(request_form, venue, request.user)
                messages.success(
                    request,
                    "Eure Anfrage ist verschickt. Der Raumgeber antwortet direkt an eure Antwort-Adresse oder über unseren Link.",
                )
                return redirect("venues:detail", pk=pk)

    map_points = []
    if venue.has_location and has_access:
        map_points = [{"lat": float(venue.latitude), "lon": float(venue.longitude), "name": venue.name, "url": ""}]
    return render(
        request,
        "venues/detail.html",
        {
            "venue": venue,
            "has_access": has_access,
            "open_request": open_request,
            "last_request": own_requests.first(),
            "request_form": request_form,
            "map_points": map_points,
            "is_bookmarked": request.user.bookmarks.filter(venue=venue).exists(),
        },
    )


def series_targets(data, accessible):
    """Orte, die zur Suche passen und Anfragen über die Plattform annehmen (öffentlich mit E-Mail oder nicht öffentlich)."""
    return [v for v in search_venues(data, accessible) if v.accepts_platform_requests]


@group_required
def series_request(request):
    """Reihenanfrage: dieselbe Anfrage geht nacheinander an mehrere passende Orte, nie gleichzeitig."""
    search_form = SearchForm(request.GET or None)
    data = search_form.cleaned_data if search_form.is_valid() else {}
    if not (data.get("district") or data.get("quarter")):
        messages.error(request, "Bitte wählt zuerst einen Stadtbezirk oder Stadtteil aus. Dann können wir passende Orte anfragen.")
        return redirect(f"{reverse('venues:search')}?{request.GET.urlencode()}")
    accessible = Venue.objects.accessible_ids(request.user)
    targets = series_targets(data, accessible)[: settings.MAX_SERIES_TARGETS]
    form = SeriesRequestForm(request.POST or None, user=request.user, targets=targets, initial={"reply_email": request.user.email})
    if request.method == "POST" and targets:
        if is_limited(request, f"usage:{request.user.pk}", limit=settings.MAX_USAGE_REQUESTS_PER_DAY, window_seconds=86400):
            messages.error(request, "Ihr habt heute schon viele Anfragen geschickt. Bitte versucht es morgen wieder.")
        elif form.is_valid():
            _, created = create_series_request(form, form.ordered_venues(), request.user)
            messages.success(
                request,
                f"Wir haben den ersten Ort angefragt. {len(created) - 1} weitere Orte sind eingereiht und werden nur "
                "angefragt, wenn der vorige absagt oder nicht antwortet.",
            )
            return redirect("venues:my_requests")
    return render(
        request,
        "venues/series_request.html",
        {"form": form, "targets": targets, "querystring": request.GET.urlencode(), "max_targets": settings.MAX_SERIES_TARGETS},
    )


@group_required
def my_requests(request):
    items = request.user.usage_requests.select_related("venue", "room").order_by("-created_at", "queue_position")
    return render(request, "venues/my_requests.html", {"items": items})


@require_POST
@group_required
def request_action(request, pk):
    """Aktionen der Gruppe: zurückziehen, Antwort vermerken, Reihe beenden."""
    item = get_object_or_404(UsageRequest.objects.select_related("venue"), pk=pk, user=request.user)
    action = request.POST.get("action")
    S = UsageRequest.Status
    if action == "withdraw" and item.status in (S.OPEN, S.QUEUED, S.ACCEPTED):
        withdraw_usage_request(item)
        messages.success(request, "Die Anfrage ist zurückgezogen. Der Termin ist für neue Anfragen wieder frei.")
    elif action in ("zugesagt", "abgesagt") and item.status == S.OPEN:
        mark_outcome_by_group(item, action)
        messages.success(request, "Danke, wir haben die Antwort vermerkt.")
    elif action == "end_series" and item.batch:
        end_series(item)
        messages.success(request, "Die Reihe ist beendet. Es werden keine weiteren Orte angefragt.")
    else:
        messages.error(request, "Diese Aktion ist für die Anfrage nicht möglich.")
    return redirect("venues:my_requests")


def respond(request, token):
    """Raumgeber sagt einer Nutzungsanfrage zu oder ab (Link aus der E-Mail, kein Konto nötig)."""
    item = UsageRequest.from_token(token)
    if item is None or item.status != UsageRequest.Status.OPEN or item.expires_at < timezone.now():
        return render(request, "venues/respond_invalid.html", status=404)
    form = RespondForm(request.POST or None)
    action = request.POST.get("action")
    if request.method == "POST" and action in ("accept", "decline") and form.is_valid():
        answer_usage_request(item, accept=action == "accept", note=form.cleaned_data["note"])
        return render(request, "venues/respond_done.html", {"accepted": action == "accept", "item": item})
    return render(request, "venues/respond.html", {"item": item, "form": form, "group": getattr(item.user, "group_profile", None)})


@require_POST
@group_required
def toggle_bookmark(request, pk):
    venue = get_object_or_404(Venue.objects.listed(), pk=pk)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, venue=venue)
    if not created:
        bookmark.delete()
    next_url = request.POST.get("next", "")
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = venue.get_absolute_url()
    return redirect(next_url)


@group_required
def bookmarks(request):
    items = request.user.bookmarks.filter(venue__status__in=Venue.VISIBLE_STATUSES).select_related("venue")
    return render(request, "venues/bookmarks.html", {"items": items})


# --- Raumgeber: Ort melden und verwalten ---------------------------------------


def submit(request):
    venue = Venue(source=Venue.Source.FORM, status=Venue.Status.UNCONFIRMED)
    form = SubmissionForm(request.POST or None, instance=venue)
    formset = RoomFormSet(request.POST or None, instance=venue, prefix="rooms")
    if request.method == "POST":
        if is_limited(request, "submit", limit=5):
            messages.error(request, "Zu viele Meldungen in kurzer Zeit. Bitte versuche es später erneut.")
        elif form.is_valid() and formset.is_valid():
            with transaction.atomic():
                venue = form.save(commit=False)
                venue.manager_email = venue.manager_email.lower()
                venue.consent_at = timezone.now()
                venue.consent_text = form.fields["consent"].label
                venue.save()
                formset.instance = venue
                formset.save()
            send_submission_confirmation(venue)
            return render(request, "venues/submit_done.html", {"email": venue.manager_email})
    return render(request, "venues/submit.html", {"form": form, "formset": formset, "quarters": ALL_QUARTERS})


def manage(request, token):
    venue = Venue.from_token(token)
    if venue is None or venue.status == Venue.Status.REJECTED:
        return render(request, "venues/manage_invalid.html", status=404)

    needs_consent = venue.consent_at is None
    action = request.POST.get("action") if request.method == "POST" else None

    if action == "confirm_email" and venue.status == Venue.Status.UNCONFIRMED:
        venue.status = Venue.Status.REVIEW
        venue.edit_token_expires_at = None
        venue.last_confirmed_at = timezone.now()
        venue.save()
        notify_moderation("Neuer Ort zur Prüfung", f"Ein Ort wurde gemeldet und bestätigt: {venue.name}")
        messages.success(request, "Danke! Deine E-Mail-Adresse ist bestätigt. Wir prüfen den Eintrag und melden uns.")
        return redirect("venues:manage", token=token)

    if action == "still_current" and venue.status in (Venue.Status.LISTED, Venue.Status.PAUSED):
        was_paused_for_silence = venue.status == Venue.Status.PAUSED and venue.paused_reason
        if was_paused_for_silence:
            venue.status = Venue.Status.LISTED
            venue.save(update_fields=["status", "updated_at"])
        confirm_still_current(venue)
        messages.success(request, "Danke! Wir haben vermerkt, dass das Angebot noch aktuell ist.")
        return redirect("venues:manage", token=token)

    if action == "pause" and venue.status == Venue.Status.LISTED:
        venue.status = Venue.Status.PAUSED
        venue.save()
        messages.success(request, "Der Eintrag ist pausiert und für Gruppen nicht mehr sichtbar.")
        return redirect("venues:manage", token=token)

    if action == "resume" and venue.status == Venue.Status.PAUSED:
        venue.status = Venue.Status.LISTED
        venue.save(update_fields=["status", "updated_at"])
        confirm_still_current(venue)
        messages.success(request, "Der Eintrag ist wieder sichtbar.")
        return redirect("venues:manage", token=token)

    if action == "remove":
        close_open_requests(venue, ListingRequest.Outcome.DECLINED)
        venue.minimize_after_rejection()
        return render(request, "venues/manage_removed.html")

    form = VenueForm(request.POST if action == "save" else None, instance=venue)
    formset = RoomFormSet(request.POST if action == "save" else None, instance=venue, prefix="rooms")
    consent_form = ConsentForm(request.POST if action == "save" and needs_consent else None)

    if action == "save":
        consent_ok = consent_form.is_valid() if needs_consent else True
        if form.is_valid() and formset.is_valid() and consent_ok:
            with transaction.atomic():
                venue = form.save(commit=False)
                now = timezone.now()
                if needs_consent:
                    venue.consent_at = now
                    venue.consent_text = consent_form.fields["consent"].label
                if venue.status == Venue.Status.PUBLIC_SOURCE:
                    # War schon sichtbar und geprüft; mit Zustimmung jetzt bestätigt.
                    venue.status = Venue.Status.LISTED
                    venue.edit_token_expires_at = None
                elif venue.status in (Venue.Status.RESEARCHED, Venue.Status.REQUESTED, Venue.Status.UNCONFIRMED):
                    venue.status = Venue.Status.REVIEW
                    # Nach der Zustimmung bleibt der Link dauerhaft gültig (bis ein neuer angefordert wird).
                    venue.edit_token_expires_at = None
                venue.last_confirmed_at = now
                venue.freshness_check_sent_at = venue.freshness_reminder_sent_at = None
                venue.save()
                formset.save()
                if venue.listing_requests.filter(outcome=ListingRequest.Outcome.OPEN).exists():
                    notify_moderation("Ort hat der Listung zugestimmt", f"Zustimmung erhalten: {venue.name}")
                close_open_requests(venue, ListingRequest.Outcome.ACCEPTED)
            messages.success(request, "Gespeichert. Vielen Dank!")
            return redirect("venues:manage", token=token)
        messages.error(request, "Bitte prüfe die markierten Felder.")

    return render(
        request,
        "venues/manage.html",
        {
            "venue": venue,
            "form": form,
            "formset": formset,
            "consent_form": consent_form,
            "needs_consent": needs_consent,
            "open_usage_requests": venue.usage_requests.filter(status=UsageRequest.Status.OPEN).count(),
            "quarters": ALL_QUARTERS,
        },
    )


def request_link(request):
    form = RequestLinkForm(request.POST or None)
    if request.method == "POST":
        if is_limited(request, "request_link", limit=5):
            messages.error(request, "Zu viele Anfragen. Bitte versuche es später erneut.")
        elif form.is_valid():
            venues = Venue.objects.filter(
                manager_email__iexact=form.cleaned_data["email"],
                status__in=[
                    Venue.Status.REQUESTED, Venue.Status.REVIEW, Venue.Status.LISTED, Venue.Status.PAUSED,
                    Venue.Status.PUBLIC_SOURCE,
                ],
            )
            for venue in venues:
                send_new_edit_link(venue)
            # Immer dieselbe Antwort, damit sich nicht ausprobieren lässt, welche Adressen hinterlegt sind.
            return render(request, "venues/request_link_done.html")
    return render(request, "venues/request_link.html", {"form": form})
