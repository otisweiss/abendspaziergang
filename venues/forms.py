from django import forms
from django.forms import inlineformset_factory

from .koeln import ALL_QUARTERS, DISTRICTS
from .models import Equipment, Purpose, Room, TimeSlot, UsageRequest, Venue

SLOT_CHOICES = [
    (f"{day}-{period}", f"{day_label} {period_label}")
    for day, day_label in TimeSlot.Day.choices
    for period, period_label in TimeSlot.Period.choices
]

CONSENT_TEXT = (
    "Ich bin berechtigt, diesen Ort anzubieten, und stimme zu, dass die Angaben freigeschalteten "
    "Gruppen auf der Plattform angezeigt werden. Ich kann den Eintrag jederzeit über den "
    "Bearbeitungslink ändern, pausieren oder entfernen."
)


class HoneypotMixin(forms.Form):
    """Unsichtbares Feld gegen Spam-Bots, ersetzt ein Captcha von Drittanbietern."""

    website_url = forms.CharField(
        required=False,
        label="Bitte leer lassen",
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
    )

    def clean_website_url(self):
        if self.cleaned_data.get("website_url"):
            raise forms.ValidationError("Spam-Verdacht.")
        return ""


class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = [
            "visibility", "public_title",
            "name", "operator", "operator_type", "description", "website",
            "street", "postcode", "quarter", "district", "transit",
            "step_free", "elevator", "accessible_wc", "hearing_loop", "disabled_parking", "accessibility_notes",
            "contact_email", "contact_phone", "contact_url", "contact_notes",
        ]
        widgets = {
            "visibility": forms.RadioSelect,
            "street": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "contact_email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "contact_phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "quarter": forms.TextInput(attrs={"list": "quarters"}),
            "postcode": forms.TextInput(attrs={"inputmode": "numeric", "pattern": "5[01][0-9]{3}"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["operator_type"].required = True
        self.fields["street"].required = True
        self.quarters = ALL_QUARTERS

    def clean(self):
        data = super().clean()
        if data.get("visibility") == Venue.Visibility.ON_REQUEST:
            if not data.get("quarter"):
                self.add_error("quarter", "Bei nicht öffentlichen Orten brauchen wir den Stadtteil. Nur er wird angezeigt.")
        elif not any(data.get(f) for f in ("contact_email", "contact_phone", "contact_url")):
            raise forms.ValidationError(
                "Bitte gib mindestens einen Kontaktweg an: E-Mail, Telefon oder eine Seite für Anfragen."
            )
        return data


class SlotField(forms.MultipleChoiceField):
    widget = forms.CheckboxSelectMultiple

    def __init__(self, **kwargs):
        super().__init__(choices=SLOT_CHOICES, required=False, label="Wann ist der Raum grundsätzlich nutzbar?", **kwargs)


class RoomForm(forms.ModelForm):
    slots = SlotField()

    class Meta:
        model = Room
        fields = ["name", "capacity", "area_sqm", "cost", "price_notes", "rhythm", "purposes", "equipment", "hours_notes"]
        widgets = {
            "purposes": forms.CheckboxSelectMultiple,
            "equipment": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["slots"] = self.instance.slot_codes()

    def slot_rows(self):
        """Gibt die Häkchen als Tabelle Wochentag × Tagesabschnitt für das Template zurück."""
        field = self["slots"]
        selected = set(field.value() or [])
        rows = []
        for day, day_label in TimeSlot.Day.choices:
            cells = []
            for period, period_label in TimeSlot.Period.choices:
                code = f"{day}-{period}"
                cells.append({"code": code, "checked": code in selected, "label": f"{day_label}, {period_label}"})
            rows.append({"label": day_label, "cells": cells})
        return rows

    def save(self, commit=True):
        room = super().save(commit=commit)
        if commit:
            self.save_slots(room)
        return room

    def save_slots(self, room):
        codes = set(self.cleaned_data.get("slots") or [])
        room.slots.all().delete()
        TimeSlot.objects.bulk_create(
            [TimeSlot(room=room, day=int(c.split("-")[0]), period=c.split("-")[1]) for c in sorted(codes)]
        )


RoomFormSet = inlineformset_factory(
    Venue, Room, form=RoomForm, extra=1, can_delete=True, min_num=1, validate_min=True
)


class BatchRequestForm(forms.ModelForm):
    """Sammelanfrage an alle passenden nicht öffentlichen Orte."""

    privacy = forms.BooleanField(
        label="Ich bin einverstanden, dass die angefragten Raumgeber den Namen unserer Gruppe, meine Nachricht und "
        "die Antwort-Adresse bekommen."
    )

    class Meta:
        model = UsageRequest
        fields = ["occasion", "dates", "persons", "message", "reply_email"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4}), "reply_email": forms.EmailInput(attrs={"autocomplete": "email"})}


class UsageRequestForm(forms.ModelForm):
    privacy = forms.BooleanField(
        label="Ich bin einverstanden, dass der Raumgeber den Namen unserer Gruppe, meine Nachricht und die "
        "Antwort-Adresse bekommt."
    )

    class Meta:
        model = UsageRequest
        fields = ["room", "occasion", "dates", "persons", "message", "reply_email"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4}), "reply_email": forms.EmailInput(attrs={"autocomplete": "email"})}

    def __init__(self, *args, venue, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = venue.rooms.all()
        self.fields["room"].empty_label = "egal / weiß nicht"
        self.fields["persons"].min_value = 1


class SubmissionForm(HoneypotMixin, VenueForm):
    """Öffentliches Formular „Ort melden“."""

    manager_email = forms.EmailField(
        label="Deine E-Mail-Adresse für die Verwaltung des Eintrags",
        help_text="Hierhin schicken wir den Bestätigungs- und Bearbeitungslink. Sie wird nicht angezeigt.",
    )
    consent = forms.BooleanField(label=CONSENT_TEXT)
    privacy = forms.BooleanField(label="Ich habe die Datenschutzhinweise gelesen.")

    class Meta(VenueForm.Meta):
        fields = VenueForm.Meta.fields + ["manager_email"]


class RespondForm(forms.Form):
    note = forms.CharField(
        label="Nachricht an die Gruppe (freiwillig)",
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="z. B. ein Terminvorschlag oder wie ihr euch abstimmt.",
    )


class ConsentForm(forms.Form):
    consent = forms.BooleanField(label=CONSENT_TEXT)


class RequestLinkForm(HoneypotMixin):
    email = forms.EmailField(label="E-Mail-Adresse, mit der der Eintrag verwaltet wird")


class SearchForm(forms.Form):
    MAX_COST_CHOICES = [
        ("", "egal"),
        ("0", "nur kostenlos"),
        ("1", "kostenlos oder gegen Spende"),
        ("2", "auch ermäßigt für Gemeinnützige"),
    ]

    q = forms.CharField(label="Suchbegriff", required=False)
    district = forms.ChoiceField(label="Stadtbezirk", required=False, choices=[("", "alle")] + DISTRICTS)
    quarter = forms.ChoiceField(label="Stadtteil", required=False, choices=[("", "alle")] + [(q, q) for q in ALL_QUARTERS])
    purpose = forms.ModelChoiceField(label="Wofür?", required=False, queryset=Purpose.objects.all(), empty_label="egal")
    capacity = forms.IntegerField(label="Personen mindestens", required=False, min_value=1, max_value=5000)
    max_cost = forms.ChoiceField(label="Kosten", required=False, choices=MAX_COST_CHOICES)
    operator_type = forms.ChoiceField(
        label="Träger", required=False, choices=[("", "alle")] + list(Venue.OperatorType.choices)
    )
    day = forms.TypedChoiceField(
        label="Wochentag", required=False, coerce=int, empty_value=None, choices=[("", "egal")] + list(TimeSlot.Day.choices)
    )
    period = forms.ChoiceField(label="Tageszeit", required=False, choices=[("", "egal")] + list(TimeSlot.Period.choices))
    step_free = forms.BooleanField(label="Stufenlos erreichbar", required=False)
    accessible_wc = forms.BooleanField(label="Barrierefreies WC", required=False)
    visibility = forms.ChoiceField(
        label="Art der Listung",
        required=False,
        choices=[("", "alle"), ("oeffentlich", "nur öffentliche Orte"), ("auf_anfrage", "nur Orte auf Anfrage (z. B. privat)")],
    )
    equipment = forms.ModelMultipleChoiceField(
        label="Ausstattung (alle gewählten)",
        required=False,
        queryset=Equipment.objects.all(),
        widget=forms.CheckboxSelectMultiple,
    )
