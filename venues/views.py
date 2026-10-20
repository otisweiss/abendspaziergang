from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ConsentForm, RequestLinkForm, RoomFormSet, SearchForm, SubmissionForm, VenueForm
from .koeln import ALL_QUARTERS, DISTRICTS
from .models import Bookmark, ListingRequest, Venue
from .ratelimit import is_limited
from .search import search_venues
from .services import close_open_requests, send_new_edit_link, send_submission_confirmation


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
        "collected_count": Venue.objects.exclude(status=Venue.Status.REJECTED).count(),
        "districts": districts,
    }
    return render(request, "pages/home.html", context)


# --- Suche für Gruppen --------------------------------------------------------


@group_required
def search(request):
    form = SearchForm(request.GET or None)
    data = form.cleaned_data if form.is_valid() else {}
    results = search_venues(data)
    page = Paginator(results, 20).get_page(request.GET.get("seite"))
    query = request.GET.copy()
    query.pop("seite", None)
    map_points = [
        {"lat": float(v.latitude), "lon": float(v.longitude), "name": v.name, "url": v.get_absolute_url()}
        for v in page
        if v.has_location
    ]
    bookmarked = set(request.user.bookmarks.values_list("venue_id", flat=True))
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
        },
    )


@group_required
def detail(request, pk):
    venue = get_object_or_404(Venue.objects.prefetch_related("rooms__equipment", "rooms__purposes", "rooms__slots"), pk=pk)
    if not venue.is_visible and not request.user.is_staff:
        raise Http404
    map_points = []
    if venue.has_location:
        map_points = [{"lat": float(venue.latitude), "lon": float(venue.longitude), "name": venue.name, "url": ""}]
    return render(
        request,
        "venues/detail.html",
        {
            "venue": venue,
            "map_points": map_points,
            "is_bookmarked": request.user.bookmarks.filter(venue=venue).exists(),
        },
    )


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
    items = request.user.bookmarks.filter(venue__status=Venue.Status.LISTED).select_related("venue")
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
        messages.success(request, "Danke! Deine E-Mail-Adresse ist bestätigt. Wir prüfen den Eintrag und melden uns.")
        return redirect("venues:manage", token=token)

    if action == "pause" and venue.status == Venue.Status.LISTED:
        venue.status = Venue.Status.PAUSED
        venue.save()
        messages.success(request, "Der Eintrag ist pausiert und für Gruppen nicht mehr sichtbar.")
        return redirect("venues:manage", token=token)

    if action == "resume" and venue.status == Venue.Status.PAUSED:
        venue.status = Venue.Status.LISTED
        venue.last_confirmed_at = timezone.now()
        venue.save()
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
                if venue.status in (Venue.Status.RESEARCHED, Venue.Status.REQUESTED, Venue.Status.UNCONFIRMED):
                    venue.status = Venue.Status.REVIEW
                    # Nach der Zustimmung bleibt der Link dauerhaft gültig (bis ein neuer angefordert wird).
                    venue.edit_token_expires_at = None
                venue.last_confirmed_at = now
                venue.save()
                formset.save()
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
                status__in=[Venue.Status.REQUESTED, Venue.Status.REVIEW, Venue.Status.LISTED, Venue.Status.PAUSED],
            )
            for venue in venues:
                send_new_edit_link(venue)
            # Immer dieselbe Antwort, damit sich nicht ausprobieren lässt, welche Adressen hinterlegt sind.
            return render(request, "venues/request_link_done.html")
    return render(request, "venues/request_link.html", {"form": form})
