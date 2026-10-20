from django.db.models import Count, Max, Min, Q

from .models import Room, Venue


def search_venues(data, accessible_ids=frozenset()):
    """Wendet die bereinigten Daten des Suchformulars an.

    Raumbezogene Filter (Zweck, Größe, Kosten, Zeit, Ausstattung) müssen alle auf
    *denselben* Raum zutreffen, sonst würde ein Ort mit kleinem Klavierraum und
    großem Saal ohne Klavier fälschlich als „großer Raum mit Klavier“ erscheinen.
    """
    venues = Venue.objects.listed()

    if q := data.get("q"):
        # Bei nicht öffentlichen Orten darf die Suche Name und Adresse nicht verraten.
        detail_match = Q(name__icontains=q) | Q(operator__icontains=q) | Q(street__icontains=q)
        open_match = Q(description__icontains=q) | Q(quarter__icontains=q) | Q(rooms__name__icontains=q) | Q(public_title__icontains=q)
        venues = venues.filter(open_match | (detail_match & (Q(visibility=Venue.Visibility.PUBLIC) | Q(pk__in=accessible_ids))))
    if district := data.get("district"):
        venues = venues.filter(district=district)
    if quarter := data.get("quarter"):
        venues = venues.filter(quarter__iexact=quarter)
    if operator_type := data.get("operator_type"):
        venues = venues.filter(operator_type=operator_type)
    if data.get("step_free"):
        venues = venues.filter(step_free=True)
    if data.get("accessible_wc"):
        venues = venues.filter(accessible_wc=True)
    if visibility := data.get("visibility"):
        venues = venues.filter(visibility=visibility)

    rooms = Room.objects.filter(venue__status__in=Venue.VISIBLE_STATUSES)
    room_filtered = False
    if purpose := data.get("purpose"):
        rooms = rooms.filter(purposes=purpose)
        room_filtered = True
    if capacity := data.get("capacity"):
        rooms = rooms.filter(capacity__gte=capacity)
        room_filtered = True
    if (max_cost := data.get("max_cost")) not in (None, ""):
        rooms = rooms.filter(cost__lte=int(max_cost))
        room_filtered = True
    day, period = data.get("day"), data.get("period")
    if day is not None or period:
        slot_filter = {}
        if day is not None:
            slot_filter["slots__day"] = day
        if period:
            slot_filter["slots__period"] = period
        rooms = rooms.filter(**slot_filter)
        room_filtered = True
    for item in data.get("equipment") or []:
        rooms = rooms.filter(equipment=item)
        room_filtered = True

    if room_filtered:
        venues = venues.filter(pk__in=rooms.values("venue_id"))

    return (
        venues.distinct()
        .annotate(room_count=Count("rooms", distinct=True), max_capacity=Max("rooms__capacity"), min_cost=Min("rooms__cost"))
        .order_by("name")
    )
