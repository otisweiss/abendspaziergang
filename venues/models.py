import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .koeln import DISTRICTS, district_for_quarter


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Equipment(models.Model):
    """Ausstattungsmerkmal, z. B. Klavier, Beamer, Küche. Pflege in der Verwaltung."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Ausstattung"
        verbose_name_plural = "Ausstattung"

    def __str__(self):
        return self.name


class Purpose(models.Model):
    """Nutzungszweck, z. B. Chorprobe, Stammtisch, Infoabend."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Nutzungszweck"
        verbose_name_plural = "Nutzungszwecke"

    def __str__(self):
        return self.name


class VenueQuerySet(models.QuerySet):
    def listed(self):
        """Für Gruppen sichtbare Orte: bestätigt oder aus öffentlicher Quelle."""
        return self.filter(status__in=Venue.VISIBLE_STATUSES)

    def confirmed(self):
        return self.filter(status=Venue.Status.LISTED)

    def accessible_ids(self, user):
        """IDs nicht öffentlicher Orte, deren Details diese Gruppe sehen darf (Anfrage bestätigt)."""
        if not user.is_authenticated:
            return set()
        return set(
            UsageRequest.objects.filter(user=user, status=UsageRequest.Status.ACCEPTED).values_list("venue_id", flat=True)
        )


class Venue(models.Model):
    class Status(models.TextChoices):
        RESEARCHED = "recherchiert", "Recherchiert (intern)"
        REQUESTED = "angefragt", "Listung angefragt"
        UNCONFIRMED = "unbestaetigt", "Gemeldet, E-Mail unbestätigt"
        REVIEW = "pruefung", "Zugestimmt, in redaktioneller Prüfung"
        PUBLIC_SOURCE = "quelle", "Aus öffentlicher Quelle (sichtbar, vom Ort noch nicht bestätigt)"
        LISTED = "gelistet", "Gelistet (sichtbar, vom Ort bestätigt)"
        PAUSED = "pausiert", "Pausiert"
        REJECTED = "abgelehnt", "Abgelehnt / nicht anfragen"

    class OperatorType(models.TextChoices):
        PUBLIC = "oeffentlich", "Öffentlich / städtisch"
        CHURCH = "kirchlich", "Kirchlich / religiöse Gemeinde"
        NONPROFIT = "gemeinnuetzig", "Verein / gemeinnütziger Träger"
        GASTRO = "gastronomie", "Gastronomie"
        BUSINESS = "unternehmen", "Unternehmen"
        PRIVATE = "privat", "Privat"

    class Visibility(models.TextChoices):
        PUBLIC = "oeffentlich", "Öffentlich gelistet: Gruppen sehen Name, Adresse und Kontakt"
        ON_REQUEST = "auf_anfrage", "Nicht öffentlich: Gruppen sehen nur Stadtteil und Raum, Details erst nach meiner Zusage"

    class Source(models.TextChoices):
        RESEARCH = "recherche", "Handrecherche"
        OSM = "osm", "OpenStreetMap-Import"
        CSV = "csv", "CSV-Import"
        FORM = "formular", "Meldeformular"

    # Stammdaten
    visibility = models.CharField(
        "Sichtbarkeit", max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    public_title = models.CharField(
        "Titel für die nicht öffentliche Anzeige",
        max_length=120,
        blank=True,
        help_text="Ohne Namen und Adresse, z. B. „Großes Wohnzimmer mit Flügel“. Nur bei nicht öffentlichen Orten.",
    )
    name = models.CharField("Name des Ortes", max_length=200)
    operator = models.CharField("Träger / Betreiber", max_length=200, blank=True)
    operator_type = models.CharField("Art des Trägers", max_length=20, choices=OperatorType.choices, blank=True)
    description = models.TextField(
        "Beschreibung",
        blank=True,
        max_length=3000,
        help_text="Bei nicht öffentlichen Orten bitte ohne Namen, Adresse oder Telefonnummer.",
    )
    website = models.URLField("Webseite", blank=True)

    # Lage
    street = models.CharField("Straße und Hausnummer", max_length=200, blank=True)
    postcode = models.CharField("PLZ", max_length=5, blank=True)
    quarter = models.CharField("Stadtteil", max_length=80, blank=True)
    district = models.CharField("Stadtbezirk", max_length=20, choices=DISTRICTS, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    transit = models.CharField("Mit Bus und Bahn", max_length=200, blank=True, help_text="z. B. „Haltestelle Körnerstraße: Linien 3 und 4“")

    # Barrierefreiheit (für den ganzen Ort)
    step_free = models.BooleanField("Stufenlos erreichbar", default=False)
    accessible_wc = models.BooleanField("Barrierefreies WC", default=False)
    hearing_loop = models.BooleanField("Induktionsschleife / Hörhilfe", default=False)
    elevator = models.BooleanField("Aufzug vorhanden (falls Räume nicht im Erdgeschoss)", default=False)
    disabled_parking = models.BooleanField("Behindertenparkplatz in der Nähe", default=False)
    accessibility_notes = models.CharField("Hinweise zur Barrierefreiheit", max_length=300, blank=True)

    # Kontaktweg für Gruppen (nur für freigeschaltete Gruppen sichtbar)
    contact_email = models.EmailField(
        "E-Mail für Raumanfragen",
        blank=True,
        help_text="Bitte möglichst eine Funktionsadresse, z. B. raumvergabe@…",
    )
    contact_phone = models.CharField("Telefon für Raumanfragen", max_length=40, blank=True)
    contact_url = models.URLField("Online-Formular / Seite für Raumanfragen", blank=True)
    contact_notes = models.CharField(
        "Hinweise zur Anfrage", max_length=500, blank=True, help_text="z. B. „Anfragen bitte mindestens 4 Wochen vorher“"
    )

    # Verwaltung des Eintrags (nie öffentlich)
    manager_email = models.EmailField(
        "E-Mail für die Verwaltung des Eintrags",
        blank=True,
        help_text="Hierhin schicken wir den Bearbeitungslink. Wird nicht angezeigt.",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESEARCHED, db_index=True)
    source = models.CharField("Herkunft", max_length=20, choices=Source.choices, default=Source.RESEARCH)
    source_reference = models.CharField(
        "Quelle", max_length=300, blank=True, help_text="URL oder Beschreibung der öffentlichen Quelle"
    )
    osm_id = models.CharField("OSM-ID", max_length=40, blank=True, db_index=True)
    internal_notes = models.TextField("Interne Notizen der Redaktion", blank=True)
    consent_at = models.DateTimeField("Zustimmung zur Veröffentlichung am", null=True, blank=True)
    consent_text = models.CharField("Wortlaut der Zustimmung", max_length=500, blank=True)
    edit_token_hash = models.CharField(max_length=64, blank=True, db_index=True, editable=False)
    edit_token_expires_at = models.DateTimeField(null=True, blank=True, editable=False)
    listing_request_count = models.PositiveSmallIntegerField("Anzahl Listungsanfragen", default=0)
    last_confirmed_at = models.DateTimeField("Zuletzt vom Raumgeber bestätigt", null=True, blank=True)
    freshness_check_sent_at = models.DateTimeField("Aktualitätsabfrage gesendet am", null=True, blank=True)
    freshness_reminder_sent_at = models.DateTimeField("Erinnerung zur Aktualität gesendet am", null=True, blank=True)
    paused_reason = models.CharField("Grund für die Pause", max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = VenueQuerySet.as_manager()

    VISIBLE_STATUSES = ("gelistet", "quelle")

    class Meta:
        ordering = ["name"]
        verbose_name = "Ort"
        verbose_name_plural = "Orte"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.quarter and not self.district:
            self.district = district_for_quarter(self.quarter)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("venues:detail", args=[self.pk])

    @property
    def is_visible(self):
        return self.status in self.VISIBLE_STATUSES

    @property
    def is_unconfirmed_source(self):
        return self.status == self.Status.PUBLIC_SOURCE

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.status == self.Status.PUBLIC_SOURCE:
            # Ohne Zustimmung dürfen nur institutionelle, öffentlich angebotene Orte sichtbar sein.
            if self.visibility != self.Visibility.PUBLIC or self.operator_type in ("", self.OperatorType.PRIVATE):
                raise ValidationError(
                    "„Aus öffentlicher Quelle“ ist nur für öffentliche Einrichtungen, Kirchen, Vereine oder Unternehmen "
                    "erlaubt, die selbst öffentlich Räume anbieten. Bitte Trägerart setzen."
                )
            if not self.source_reference:
                raise ValidationError("Bitte die öffentliche Quelle angeben (URL).")

    @property
    def is_public(self):
        return self.visibility == self.Visibility.PUBLIC

    @property
    def display_title(self):
        """Name für Gruppen ohne Zugriff auf Details."""
        if self.is_public:
            return self.name
        return self.public_title or f"Nicht öffentlicher Raum in {self.quarter or 'Köln'}"

    def needs_freshness_check_since(self):
        return self.last_confirmed_at or self.consent_at or self.created_at

    @property
    def has_location(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def address(self):
        line2 = " ".join(p for p in [self.postcode, "Köln"] if p)
        return ", ".join(p for p in [self.street, line2] if p)

    def issue_edit_token(self, valid_days=None):
        """Erzeugt einen neuen Bearbeitungslink. Gespeichert wird nur der Hash."""
        token = secrets.token_urlsafe(32)
        self.edit_token_hash = hash_token(token)
        self.edit_token_expires_at = timezone.now() + timedelta(days=valid_days) if valid_days else None
        self.save(update_fields=["edit_token_hash", "edit_token_expires_at", "updated_at"])
        return token

    def edit_url(self, token):
        return settings.SITE_URL + reverse("venues:manage", args=[token])

    @classmethod
    def from_token(cls, token):
        if not token:
            return None
        venue = cls.objects.filter(edit_token_hash=hash_token(token)).first()
        if venue is None:
            return None
        if venue.edit_token_expires_at and venue.edit_token_expires_at < timezone.now():
            return None
        return venue

    def minimize_after_rejection(self):
        """Behält nur einen Sperrvermerk (Name, Adresse), damit nicht erneut angefragt wird."""
        self.rooms.all().delete()
        self.bookmarks.all().delete()
        for field in [
            "description", "website", "transit", "accessibility_notes", "contact_email", "contact_phone",
            "contact_url", "contact_notes", "manager_email", "consent_text", "edit_token_hash", "public_title",
            "paused_reason",
        ]:
            setattr(self, field, "")
        self.step_free = self.accessible_wc = self.hearing_loop = self.elevator = self.disabled_parking = False
        self.usage_requests.all().delete()
        self.consent_at = None
        self.edit_token_expires_at = None
        self.status = self.Status.REJECTED
        self.save()


class Room(models.Model):
    class Cost(models.IntegerChoices):
        FREE = 0, "Kostenlos"
        DONATION = 1, "Gegen Spende"
        REDUCED = 2, "Ermäßigt für Gemeinnützige"
        PAID = 3, "Kostenpflichtig"
        ON_REQUEST = 4, "Kosten auf Anfrage"

    class Rhythm(models.TextChoices):
        BOTH = "beides", "Einmalig und regelmäßig"
        ONCE = "einmalig", "Nur einmalige Nutzung"
        REGULAR = "regelmaessig", "Nur regelmäßige Nutzung"

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="rooms")
    name = models.CharField("Name des Raums", max_length=120, help_text="z. B. „Großer Saal“, „Seminarraum 1“")
    capacity = models.PositiveIntegerField("Max. Personen", null=True, blank=True)
    area_sqm = models.PositiveIntegerField("Fläche in m²", null=True, blank=True)
    cost = models.PositiveSmallIntegerField("Kosten", choices=Cost.choices, default=Cost.PAID)
    price_notes = models.CharField("Preise / Konditionen", max_length=300, blank=True)
    rhythm = models.CharField("Nutzung", max_length=20, choices=Rhythm.choices, default=Rhythm.BOTH)
    equipment = models.ManyToManyField(Equipment, blank=True, verbose_name="Ausstattung")
    purposes = models.ManyToManyField(Purpose, blank=True, verbose_name="Geeignet für")
    hours_notes = models.CharField(
        "Zeiten genauer", max_length=300, blank=True, help_text="z. B. „Mo–Fr 9–22 Uhr, Wochenende nach Absprache“"
    )

    class Meta:
        ordering = ["venue", "name"]
        verbose_name = "Raum"
        verbose_name_plural = "Räume"

    def __str__(self):
        return f"{self.venue.name} – {self.name}"

    def slot_codes(self):
        return [s.code for s in self.slots.all()]


class TimeSlot(models.Model):
    """Grobe Verfügbarkeit: Wochentag × Tagesabschnitt. Dient der Filterung."""

    class Day(models.IntegerChoices):
        MON = 0, "Montag"
        TUE = 1, "Dienstag"
        WED = 2, "Mittwoch"
        THU = 3, "Donnerstag"
        FRI = 4, "Freitag"
        SAT = 5, "Samstag"
        SUN = 6, "Sonntag"

    class Period(models.TextChoices):
        MORNING = "vormittag", "Vormittag (8–12 Uhr)"
        AFTERNOON = "nachmittag", "Nachmittag (12–17 Uhr)"
        EVENING = "abend", "Abend (17–22 Uhr)"
        LATE = "spaet", "Spät (ab 22 Uhr)"

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="slots")
    day = models.PositiveSmallIntegerField(choices=Day.choices)
    period = models.CharField(max_length=12, choices=Period.choices)

    class Meta:
        ordering = ["day", "period"]
        constraints = [models.UniqueConstraint(fields=["room", "day", "period"], name="unique_room_slot")]
        verbose_name = "Zeitfenster"
        verbose_name_plural = "Zeitfenster"

    @property
    def code(self):
        return f"{self.day}-{self.period}"

    def __str__(self):
        return f"{self.get_day_display()} {self.get_period_display()}"


class ListingRequest(models.Model):
    """Protokoll einer Anfrage an einen recherchierten Ort (Nachweis und Begrenzung)."""

    class Outcome(models.TextChoices):
        OPEN = "offen", "Offen"
        ACCEPTED = "zugestimmt", "Zugestimmt"
        DECLINED = "abgelehnt", "Abgelehnt"
        EXPIRED = "abgelaufen", "Ohne Antwort abgelaufen"

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="listing_requests")
    recipient = models.EmailField("Empfänger")
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    expires_at = models.DateTimeField()
    outcome = models.CharField(max_length=12, choices=Outcome.choices, default=Outcome.OPEN)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-sent_at"]
        verbose_name = "Listungsanfrage"
        verbose_name_plural = "Listungsanfragen"

    def __str__(self):
        return f"{self.venue} ({self.sent_at:%d.%m.%Y})"


class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks")
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "venue"], name="unique_bookmark")]
        verbose_name = "Merklisten-Eintrag"
        verbose_name_plural = "Merkliste"


class UsageRequest(models.Model):
    """Nutzungsanfrage einer Gruppe an einen nicht öffentlichen Ort.

    Der Raumgeber bekommt die Anfrage per E-Mail und sagt zu oder ab. Erst nach der Zusage
    sieht die Gruppe Name, Adresse und Kontakt des Ortes. Die E-Mail-Adresse des Raumgebers
    bleibt bis dahin verborgen.
    """

    class Status(models.TextChoices):
        OPEN = "offen", "Wartet auf Antwort"
        ACCEPTED = "zugesagt", "Zugesagt"
        DECLINED = "abgesagt", "Abgesagt"
        EXPIRED = "abgelaufen", "Ohne Antwort abgelaufen"
        WITHDRAWN = "zurueckgezogen", "Von der Gruppe zurückgezogen"

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="usage_requests")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="usage_requests")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Raum")
    occasion = models.CharField("Wofür braucht ihr den Raum?", max_length=200)
    dates = models.CharField("Wann?", max_length=200, help_text="z. B. „Samstag, 14. März, 19–22 Uhr“ oder „jeden Dienstagabend“")
    persons = models.PositiveIntegerField("Wie viele Personen?")
    message = models.TextField(
        "Nachricht an den Raumgeber",
        max_length=1500,
        blank=True,
        help_text="Stellt euch kurz vor. Bitte keine Daten anderer Personen.",
    )
    reply_email = models.EmailField("Antwort an diese E-Mail-Adresse")
    batch = models.CharField("Sammelanfrage", max_length=32, blank=True, db_index=True, editable=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    response_note = models.CharField("Antwort des Raumgebers", max_length=500, blank=True)
    token_hash = models.CharField(max_length=64, db_index=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Nutzungsanfrage"
        verbose_name_plural = "Nutzungsanfragen"

    def __str__(self):
        return f"Anfrage an {self.venue.display_title} ({self.get_status_display()})"

    def issue_token(self):
        token = secrets.token_urlsafe(32)
        self.token_hash = hash_token(token)
        return token

    def respond_url(self, token):
        return settings.SITE_URL + reverse("venues:respond", args=[token])

    @classmethod
    def from_token(cls, token):
        return cls.objects.filter(token_hash=hash_token(token)).select_related("venue", "user").first() if token else None
