from django.db import migrations
from django.utils.text import slugify

EQUIPMENT = [
    "Klavier / Flügel", "Beamer", "Leinwand / großer Bildschirm", "Tonanlage / Mikrofon", "WLAN", "Küche",
    "Theke / Ausschank", "Bestuhlung", "Tische", "Bühne", "Tageslicht", "Flipchart / Moderationskoffer",
    "Garderobe", "Notenständer", "Spiegel / Tanzboden", "Außenfläche / Garten", "Parkplätze",
    "Fahrradstellplätze", "Lagermöglichkeit", "Getränke vor Ort (Gastronomie)",
]

PURPOSES = [
    "Chorprobe / Musikprobe", "Gruppentreffen", "Stammtisch", "Infoabend / Vortrag", "Workshop / Seminar",
    "Mitgliederversammlung", "Vereinsfeier / Sommerfest", "Bewegung / Tanz / Yoga", "Konzert / Auftritt",
    "Selbsthilfe / Beratung", "Kinder- und Jugendgruppe", "Repair-Café / Werkstatt", "Lesung / Kultur",
]


def make_slug(name):
    for a, b in [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss"), ("/", " ")]:
        name = name.replace(a, b)
    return slugify(name)


def seed(apps, schema_editor):
    Equipment = apps.get_model("venues", "Equipment")
    Purpose = apps.get_model("venues", "Purpose")
    for i, name in enumerate(EQUIPMENT):
        Equipment.objects.get_or_create(slug=make_slug(name), defaults={"name": name, "order": i * 10})
    for i, name in enumerate(PURPOSES):
        Purpose.objects.get_or_create(slug=make_slug(name), defaults={"name": name, "order": i * 10})


class Migration(migrations.Migration):
    dependencies = [("venues", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
