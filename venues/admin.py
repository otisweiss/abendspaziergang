from django.contrib import admin, messages
from django.utils import timezone

from .models import Bookmark, Equipment, ListingRequest, Purpose, Room, TimeSlot, UsageRequest, Venue
from .services import ListingRequestError, send_listing_request, send_templated_mail


@admin.register(Equipment, Purpose)
class LookupAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "order"]
    list_editable = ["order"]
    prepopulated_fields = {"slug": ["name"]}


class TimeSlotInline(admin.TabularInline):
    model = TimeSlot
    extra = 0


class RoomInline(admin.StackedInline):
    model = Room
    extra = 0
    filter_horizontal = ["equipment", "purposes"]
    show_change_link = True


class ListingRequestInline(admin.TabularInline):
    model = ListingRequest
    extra = 0
    can_delete = False
    readonly_fields = ["recipient", "sent_at", "sent_by", "expires_at", "outcome", "answered_at"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ["name", "quarter", "district", "visibility", "status", "source", "last_confirmed_at", "updated_at"]
    list_filter = ["status", "visibility", "district", "operator_type", "source"]
    search_fields = ["name", "operator", "street", "quarter", "contact_email", "manager_email"]
    readonly_fields = [
        "consent_at", "consent_text", "listing_request_count", "last_confirmed_at", "freshness_check_sent_at",
        "freshness_reminder_sent_at", "created_at", "updated_at",
    ]
    inlines = [RoomInline, ListingRequestInline]
    actions = ["action_send_request", "action_publish", "action_public_source", "action_pause", "action_reject"]
    fieldsets = [
        (None, {"fields": ["name", "operator", "operator_type", "description", "website", "status", "paused_reason"]}),
        ("Sichtbarkeit", {"fields": ["visibility", "public_title"]}),
        ("Lage", {"fields": ["street", "postcode", "quarter", "district", ("latitude", "longitude"), "transit"]}),
        (
            "Barrierefreiheit",
            {"fields": ["step_free", "elevator", "accessible_wc", "hearing_loop", "disabled_parking", "accessibility_notes"]},
        ),
        ("Kontakt für Gruppen", {"fields": ["contact_email", "contact_phone", "contact_url", "contact_notes"]}),
        (
            "Verwaltung (nicht öffentlich)",
            {
                "fields": [
                    "manager_email", "source", "source_reference", "osm_id", "internal_notes", "consent_at",
                    "consent_text", "listing_request_count", "last_confirmed_at", "freshness_check_sent_at",
                    "freshness_reminder_sent_at", "created_at", "updated_at",
                ]
            },
        ),
    ]

    @admin.action(description="Listungsanfrage per E-Mail senden")
    def action_send_request(self, request, queryset):
        sent = 0
        for venue in queryset:
            try:
                send_listing_request(venue, sent_by=request.user)
                sent += 1
            except ListingRequestError as exc:
                self.message_user(request, str(exc), messages.WARNING)
        if sent:
            self.message_user(request, f"{sent} Anfrage(n) verschickt.", messages.SUCCESS)

    @admin.action(description="Freigeben (gelistet) und Raumgeber benachrichtigen")
    def action_publish(self, request, queryset):
        done = 0
        for venue in queryset:
            if venue.consent_at is None:
                self.message_user(request, f"„{venue}“: keine Zustimmung des Raumgebers – nicht freigegeben.", messages.WARNING)
                continue
            if venue.status == Venue.Status.LISTED:
                continue
            venue.status = Venue.Status.LISTED
            venue.save()
            if venue.manager_email:
                send_templated_mail("listed", venue.manager_email, {"venue": venue})
            done += 1
        if done:
            self.message_user(request, f"{done} Ort(e) freigegeben.", messages.SUCCESS)

    @admin.action(description="Als „aus öffentlicher Quelle“ sichtbar machen (nur Einrichtungen mit öffentlichem Raumangebot)")
    def action_public_source(self, request, queryset):
        from django.core.exceptions import ValidationError

        done = 0
        for venue in queryset.filter(status__in=[Venue.Status.RESEARCHED, Venue.Status.REQUESTED]):
            venue.status = Venue.Status.PUBLIC_SOURCE
            try:
                venue.clean()
            except ValidationError as exc:
                self.message_user(request, f"„{venue}“: {exc.messages[0]}", messages.WARNING)
                continue
            venue.save()
            done += 1
        self.message_user(request, f"{done} Ort(e) sichtbar gemacht.", messages.SUCCESS)

    @admin.action(description="Pausieren (ausblenden)")
    def action_pause(self, request, queryset):
        n = queryset.filter(status=Venue.Status.LISTED).update(status=Venue.Status.PAUSED, updated_at=timezone.now())
        self.message_user(request, f"{n} Ort(e) pausiert.")

    @admin.action(description="Ablehnen / Sperrvermerk (Daten werden minimiert)")
    def action_reject(self, request, queryset):
        for venue in queryset:
            venue.minimize_after_rejection()
        self.message_user(request, "Erledigt. Es bleiben nur Name und Adresse als Sperrvermerk.")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["name", "venue", "capacity", "cost"]
    list_filter = ["cost", "purposes"]
    search_fields = ["name", "venue__name"]
    filter_horizontal = ["equipment", "purposes"]
    inlines = [TimeSlotInline]


@admin.register(ListingRequest)
class ListingRequestAdmin(admin.ModelAdmin):
    list_display = ["venue", "recipient", "sent_at", "expires_at", "outcome"]
    list_filter = ["outcome"]
    readonly_fields = ["venue", "recipient", "sent_at", "sent_by", "expires_at", "outcome", "answered_at"]

    def has_add_permission(self, request):
        return False


@admin.register(UsageRequest)
class UsageRequestAdmin(admin.ModelAdmin):
    """Nur Metadaten. Nachrichten zwischen Gruppe und Raumgeber sieht die Redaktion nicht."""

    list_display = ["venue", "date", "status", "batch", "queue_position", "created_at", "answered_at"]
    list_filter = ["status", "confirmed_by_host"]
    fields = ["venue", "status", "date", "time_from", "time_to", "weekly", "batch", "queue_position", "persons",
              "confirmed_by_host", "created_at", "expires_at", "answered_at"]
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    # Merklisten sind Sache der Gruppen; die Redaktion sieht nur Zahlen.
    list_display = ["venue", "created_at"]

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
