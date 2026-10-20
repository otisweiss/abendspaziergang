"""Legt erfundene Beispielorte und ein Demo-Konto an – nur für Test und Vorschau.

    python manage.py demo_daten [--password geheim123456]
"""

import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import GroupProfile, User
from venues.models import Equipment, Purpose, Room, TimeSlot, Venue

DEMO = [
    # name, operator, typ, quarter, lat, lon, step_free, beschreibung, räume
    ("Beispiel: Bürgerhaus am Rhein", "Bürgerhaus-Verein e.V. (fiktiv)", "gemeinnuetzig", "Deutz", 50.9365, 6.9740, True,
     "Stadtteilzentrum mit großem Saal und zwei Gruppenräumen. Gemeinnützige Gruppen zahlen einen reduzierten Satz.",
     [("Großer Saal", 120, 140, 2, ["bestuhlung", "buehne", "tonanlage-mikrofon", "beamer", "theke-ausschank"],
       ["konzert-auftritt", "mitgliederversammlung", "vereinsfeier-sommerfest", "infoabend-vortrag"], "abend"),
      ("Gruppenraum 1", 20, 35, 1, ["tische", "bestuhlung", "flipchart-moderationskoffer", "tageslicht"],
       ["gruppentreffen", "selbsthilfe-beratung", "workshop-seminar"], "all")]),
    ("Beispiel: Pfarrsaal St. Musterkirche", "Kath. Kirchengemeinde (fiktiv)", "kirchlich", "Nippes", 50.9640, 6.9530, False,
     "Gemütlicher Pfarrsaal mit Klavier – ideal für Chorproben.",
     [("Pfarrsaal", 60, 90, 1, ["klavier-fluegel", "bestuhlung", "kueche", "notenstaender"],
       ["chorprobe-musikprobe", "gruppentreffen", "vereinsfeier-sommerfest"], "abend")]),
    ("Beispiel: Stadtteilbibliothek Musterstraße", "Stadt Köln (fiktiv)", "oeffentlich", "Kalk", 50.9405, 7.0060, True,
     "Veranstaltungsraum in der Bibliothek, kostenlos für Lesungen und Infoabende.",
     [("Veranstaltungsraum", 40, 60, 0, ["beamer", "leinwand-grosser-bildschirm", "wlan", "bestuhlung"],
       ["infoabend-vortrag", "lesung-kultur", "workshop-seminar"], "day")]),
    ("Beispiel: Brauhaus Zum Hinterzimmer", "Gastronomie (fiktiv)", "gastronomie", "Ehrenfeld", 50.9500, 6.9180, False,
     "Separates Hinterzimmer für Stammtische. Kein Mietpreis, es wird verzehrt.",
     [("Hinterzimmer", 25, 40, 0, ["tische", "getraenke-vor-ort-gastronomie"], ["stammtisch", "gruppentreffen"], "abend")]),
    ("Beispiel: Coworking Sülz am Abend", "Musterbüro GmbH (fiktiv)", "unternehmen", "Sülz", 50.9220, 6.9230, True,
     "Unser Besprechungsraum steht abends sozialen Initiativen kostenlos zur Verfügung.",
     [("Besprechungsraum", 12, 30, 0, ["beamer", "wlan", "tische", "flipchart-moderationskoffer"],
       ["gruppentreffen", "workshop-seminar", "selbsthilfe-beratung"], "abend")]),
    ("Beispiel: Jugendzentrum Porz-Mitte", "Jugendhilfe-Träger (fiktiv)", "gemeinnuetzig", "Porz", 50.8840, 7.0590, True,
     "Bewegungsraum mit Spiegelwand und Musikanlage.",
     [("Bewegungsraum", 30, 80, 1, ["spiegel-tanzboden", "tonanlage-mikrofon"], ["bewegung-tanz-yoga", "kinder-und-jugendgruppe"], "afternoon")]),
    ("Beispiel: Gemeindezentrum Chorweiler", "Ev. Gemeinde (fiktiv)", "kirchlich", "Chorweiler", 51.0270, 6.8960, True,
     "Gemeindesaal und Werkraum, auch für Repair-Cafés.",
     [("Gemeindesaal", 80, 110, 2, ["bestuhlung", "kueche", "klavier-fluegel"], ["chorprobe-musikprobe", "vereinsfeier-sommerfest", "mitgliederversammlung"], "all"),
      ("Werkraum", 15, 40, 0, ["tische", "lagermoeglichkeit"], ["repair-cafe-werkstatt"], "day")]),
    ("Beispiel: Kulturkeller Mülheim", "Kulturverein (fiktiv)", "gemeinnuetzig", "Mülheim", 50.9630, 7.0050, False,
     "Gewölbekeller mit kleiner Bühne für Konzerte und Lesungen.",
     [("Gewölbekeller", 70, 90, 3, ["buehne", "tonanlage-mikrofon", "theke-ausschank"], ["konzert-auftritt", "lesung-kultur"], "late")]),
]

PERIODS = {
    "abend": [(d, "abend") for d in range(0, 5)],
    "day": [(d, p) for d in range(0, 6) for p in ("vormittag", "nachmittag")],
    "afternoon": [(d, "nachmittag") for d in range(0, 5)],
    "late": [(d, p) for d in (3, 4, 5) for p in ("abend", "spaet")],
    "all": [(d, p) for d in range(0, 7) for p in ("vormittag", "nachmittag", "abend")],
}


class Command(BaseCommand):
    help = "Legt erfundene Beispieldaten an (nur Test/Vorschau)."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="demo-passwort-2026")

    def handle(self, password, **opts):
        now = timezone.now()
        for name, operator, op_type, quarter, lat, lon, step_free, desc, rooms in DEMO:
            if Venue.objects.filter(name=name).exists():
                continue
            venue = Venue.objects.create(
                name=name, operator=operator, operator_type=op_type, quarter=quarter, latitude=lat, longitude=lon,
                street="Musterstraße " + str(random.randint(1, 99)), postcode="50000", step_free=step_free,
                accessible_wc=step_free, description=desc, contact_email="raumanfrage@example.org",
                contact_notes="Fiktiver Beispieleintrag.", manager_email="verwaltung@example.org",
                status=Venue.Status.LISTED, source=Venue.Source.RESEARCH, consent_at=now, last_confirmed_at=now,
                consent_text="Demo",
            )
            for rname, cap, area, cost, equip, purp, period in rooms:
                room = Room.objects.create(venue=venue, name=rname, capacity=cap, area_sqm=area, cost=cost)
                room.equipment.set(Equipment.objects.filter(slug__in=equip))
                room.purposes.set(Purpose.objects.filter(slug__in=purp))
                TimeSlot.objects.bulk_create([TimeSlot(room=room, day=d, period=p) for d, p in PERIODS[period]])
        # Ein paar recherchierte (unsichtbare) Orte für die Redaktionsansicht
        for i, q in enumerate(["Lindenthal", "Rodenkirchen", "Bickendorf"]):
            Venue.objects.get_or_create(
                name=f"Beispiel: recherchierter Ort {i + 1}",
                defaults={"quarter": q, "contact_email": "info@example.org", "source_reference": "Beispielquelle"},
            )
        user, created = User.objects.get_or_create(email="demo@example.org", defaults={"is_active": True})
        user.set_password(password)
        user.save()
        GroupProfile.objects.get_or_create(
            user=user,
            defaults={
                "name": "Demo-Chor Kölsche Stimmen", "kind": GroupProfile.Kind.CHOIR, "purpose": "Wöchentliche Probe, ca. 25 Personen",
                "status": GroupProfile.Status.APPROVED, "terms_accepted_at": now,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Demodaten angelegt. Login: demo@example.org / {password}"))
