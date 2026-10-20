"""Legt ein Demo-Konto und zwei erfundene, nicht öffentliche Räume an – nur für Test und Vorschau.

Echte öffentliche Orte kommen aus `orte_importieren data/orte_koeln.json`. Private Räume lassen
sich nicht aus öffentlichen Quellen sammeln; die Beispiele zeigen deshalb nur den Ablauf
der nicht öffentlichen Listung.

    python manage.py demo_daten [--password geheim123456]
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import GroupProfile, User
from venues.models import Equipment, Purpose, Room, TimeSlot, Venue

PRIVATE_EXAMPLES = [
    {
        "name": "Beispiel (fiktiv): Wohnzimmer Familie Muster",
        "public_title": "Großes Wohnzimmer mit Flügel (fiktives Beispiel)",
        "quarter": "Ehrenfeld",
        "description": "Altbau-Wohnzimmer mit Flügel für Hauskonzerte und Lesungen bis 30 Gäste. Erfundener Beispieleintrag.",
        "room": ("Wohnzimmer", 30, 45, 1, ["klavier-fluegel", "bestuhlung"], ["konzert-auftritt", "lesung-kultur"],
                 [(4, "abend"), (5, "abend"), (6, "nachmittag")]),
    },
    {
        "name": "Beispiel (fiktiv): Atelier im Hinterhof",
        "public_title": "Helles Atelier mit Garten (fiktives Beispiel)",
        "quarter": "Ehrenfeld",
        "description": "Atelier mit großem Tisch und Garten für Workshops und kleine Gruppentreffen. Erfundener Beispieleintrag.",
        "room": ("Atelier", 15, 40, 0, ["tische", "tageslicht", "aussenflaeche-garten"], ["workshop-seminar", "gruppentreffen"],
                 [(0, "abend"), (2, "abend"), (5, "vormittag")]),
    },
]


class Command(BaseCommand):
    help = "Legt ein Demo-Konto und erfundene nicht öffentliche Räume an (nur Test/Vorschau)."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="demo-passwort-2026")

    def handle(self, password, **opts):
        now = timezone.now()
        for ex in PRIVATE_EXAMPLES:
            if Venue.objects.filter(name=ex["name"]).exists():
                continue
            venue = Venue.objects.create(
                name=ex["name"], public_title=ex["public_title"], visibility=Venue.Visibility.ON_REQUEST,
                operator_type=Venue.OperatorType.PRIVATE, quarter=ex["quarter"], street="Musterstraße 1", postcode="50823",
                description=ex["description"], contact_email="gastgeber@example.org", manager_email="gastgeber@example.org",
                status=Venue.Status.LISTED, consent_at=now, last_confirmed_at=now, consent_text="Demo",
            )
            name, cap, area, cost, equip, purp, slots = ex["room"]
            room = Room.objects.create(venue=venue, name=name, capacity=cap, area_sqm=area, cost=cost)
            room.equipment.set(Equipment.objects.filter(slug__in=equip))
            room.purposes.set(Purpose.objects.filter(slug__in=purp))
            TimeSlot.objects.bulk_create([TimeSlot(room=room, day=d, period=p) for d, p in slots])
        user, _ = User.objects.get_or_create(email="demo@example.org", defaults={"is_active": True})
        user.set_password(password)
        user.save()
        GroupProfile.objects.get_or_create(
            user=user,
            defaults={
                "name": "Demo-Chor Kölsche Stimmen", "kind": GroupProfile.Kind.CHOIR,
                "purpose": "Wöchentliche Probe, ca. 25 Personen", "status": GroupProfile.Status.APPROVED,
                "terms_accepted_at": now,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Demodaten angelegt. Login: demo@example.org / {password}"))
