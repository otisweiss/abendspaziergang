import re
from datetime import timedelta

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import GroupProfile, User

from .models import Equipment, ListingRequest, Purpose, Room, TimeSlot, UsageRequest, Venue
from .search import search_venues
from .services import ListingRequestError, expire_usage_requests, run_freshness_checks, send_listing_request


def make_group_user(email="chor@example.org", status=GroupProfile.Status.APPROVED):
    user = User.objects.create_user(email=email, password="sehr-geheimes-passwort")
    GroupProfile.objects.create(user=user, name="Testchor", kind="chor", purpose="Probe", status=status, terms_accepted_at=timezone.now())
    return user


def make_venue(name="Bürgerhaus", status=Venue.Status.LISTED, **kwargs):
    defaults = dict(street="Teststr. 1", quarter="Ehrenfeld", contact_email="raum@example.org", consent_at=timezone.now())
    defaults.update(kwargs)
    return Venue.objects.create(name=name, status=status, **defaults)


def extract_url(body):
    """Erster Link auf die eigene Seite (nicht etwa eine Quellenangabe)."""
    match = re.search(r"http://testserver/\S+", body) or re.search(r"https?://\S+", body)
    return match.group(0)


class AccessTests(TestCase):
    def test_search_requires_login(self):
        response = self.client.get(reverse("venues:search"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_pending_group_cannot_search(self):
        user = make_group_user(status=GroupProfile.Status.PENDING)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("venues:search")).status_code, 403)

    def test_only_listed_venues_visible(self):
        listed = make_venue("Sichtbar")
        hidden = make_venue("Recherchiert", status=Venue.Status.RESEARCHED)
        self.client.force_login(make_group_user())
        response = self.client.get(reverse("venues:search"))
        self.assertContains(response, "Sichtbar")
        self.assertNotContains(response, "Recherchiert")
        self.assertEqual(self.client.get(reverse("venues:detail", args=[hidden.pk])).status_code, 404)
        detail = self.client.get(reverse("venues:detail", args=[listed.pk]))
        self.assertContains(detail, "raum@example.org")

    def test_security_headers(self):
        response = self.client.get(reverse("pages:home"))
        self.assertIn("default-src 'self'", response["Content-Security-Policy"])
        self.assertNotIn("googleapis", response.content.decode())


class SearchTests(TestCase):
    def setUp(self):
        self.piano = Equipment.objects.get(slug="klavier-fluegel")
        self.beamer = Equipment.objects.get(slug="beamer")
        self.choir = Purpose.objects.get(slug="chorprobe-musikprobe")
        self.venue = make_venue("Pfarrsaal")
        small = Room.objects.create(venue=self.venue, name="Klein", capacity=10, cost=Room.Cost.FREE)
        small.equipment.add(self.piano)
        small.purposes.add(self.choir)
        TimeSlot.objects.create(room=small, day=2, period="abend")
        big = Room.objects.create(venue=self.venue, name="Saal", capacity=100, cost=Room.Cost.PAID)
        big.equipment.add(self.beamer)

    def names(self, **data):
        return [v.name for v in search_venues(data)]

    def test_room_filters_apply_to_same_room(self):
        self.assertEqual(self.names(capacity=50, equipment=[self.beamer]), ["Pfarrsaal"])
        # Großer Raum mit Klavier gibt es nicht – Klavier steht im kleinen Raum
        self.assertEqual(self.names(capacity=50, equipment=[self.piano]), [])

    def test_cost_and_time_filters(self):
        self.assertEqual(self.names(max_cost="0", day=2, period="abend"), ["Pfarrsaal"])
        self.assertEqual(self.names(max_cost="0", day=3), [])
        self.assertEqual(self.names(purpose=self.choir, capacity=11), [])

    def test_district_from_quarter(self):
        self.assertEqual(self.venue.district, "ehrenfeld")
        self.assertEqual(self.names(district="porz"), [])


class SubmissionFlowTests(TestCase):
    def post_data(self, **extra):
        data = {
            "visibility": "oeffentlich", "name": "Vereinsheim Test", "operator": "TV e.V.", "operator_type": "gemeinnuetzig", "street": "Weg 2",
            "postcode": "50823", "quarter": "Neuehrenfeld", "contact_email": "vermietung@example.org",
            "manager_email": "Vorstand@Example.org", "consent": "on", "privacy": "on",
            "rooms-TOTAL_FORMS": "1", "rooms-INITIAL_FORMS": "0", "rooms-MIN_NUM_FORMS": "1", "rooms-MAX_NUM_FORMS": "1000",
            "rooms-0-name": "Clubraum", "rooms-0-capacity": "30", "rooms-0-cost": "1", "rooms-0-rhythm": "beides",
            "rooms-0-slots": ["1-abend", "3-abend"],
        }
        data.update(extra)
        return data

    def test_submit_confirm_and_publish(self):
        response = self.client.post(reverse("venues:submit"), self.post_data())
        self.assertContains(response, "Fast geschafft")
        venue = Venue.objects.get(name="Vereinsheim Test")
        self.assertEqual(venue.status, Venue.Status.UNCONFIRMED)
        self.assertEqual(venue.manager_email, "vorstand@example.org")
        self.assertEqual(venue.rooms.get().slots.count(), 2)
        self.assertNotIn(venue.edit_token_hash, mail.outbox[0].body)

        url = extract_url(mail.outbox[0].body)
        path = url.split("testserver")[-1] if "testserver" in url else "/" + url.split("/", 3)[3]
        self.client.get(path)
        venue.refresh_from_db()
        self.assertEqual(venue.status, Venue.Status.UNCONFIRMED, "GET darf nichts bestätigen")
        self.client.post(path, {"action": "confirm_email"})
        venue.refresh_from_db()
        self.assertEqual(venue.status, Venue.Status.REVIEW)
        self.assertIsNone(venue.edit_token_expires_at)

    def test_honeypot_blocks(self):
        response = self.client.post(reverse("venues:submit"), self.post_data(website_url="http://spam"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Venue.objects.exists())

    def test_contact_required(self):
        self.client.post(reverse("venues:submit"), self.post_data(contact_email=""))
        self.assertFalse(Venue.objects.exists())


@override_settings(SITE_URL="http://testserver")
class ListingRequestTests(TestCase):
    def test_request_accept_flow(self):
        venue = make_venue("Bibliothek", status=Venue.Status.RESEARCHED, consent_at=None)
        send_listing_request(venue)
        venue.refresh_from_db()
        self.assertEqual(venue.status, Venue.Status.REQUESTED)
        path = extract_url(mail.outbox[0].body).replace("http://testserver", "")
        response = self.client.get(path)
        self.assertContains(response, "bisher nirgends zu sehen")
        data = {
            "action": "save", "visibility": "oeffentlich", "name": "Bibliothek", "operator_type": "oeffentlich", "street": "Teststr. 1",
            "contact_email": "raum@example.org", "consent": "on",
            "rooms-TOTAL_FORMS": "1", "rooms-INITIAL_FORMS": "0", "rooms-MIN_NUM_FORMS": "1", "rooms-MAX_NUM_FORMS": "1000",
            "rooms-0-name": "Lesesaal", "rooms-0-cost": "0", "rooms-0-rhythm": "beides",
        }
        self.client.post(path, data)
        venue.refresh_from_db()
        self.assertEqual(venue.status, Venue.Status.REVIEW)
        self.assertIsNotNone(venue.consent_at)
        self.assertEqual(venue.listing_requests.get().outcome, ListingRequest.Outcome.ACCEPTED)

    def test_decline_minimizes_data(self):
        venue = make_venue("Saal", status=Venue.Status.RESEARCHED, consent_at=None, description="Text")
        send_listing_request(venue)
        path = extract_url(mail.outbox[0].body).replace("http://testserver", "")
        self.client.post(path, {"action": "remove"})
        venue.refresh_from_db()
        self.assertEqual(venue.status, Venue.Status.REJECTED)
        self.assertEqual(venue.contact_email, "")
        self.assertEqual(venue.description, "")
        self.assertEqual(self.client.get(path).status_code, 404)

    @override_settings(MAX_LISTING_REQUESTS=2)
    def test_request_limit(self):
        venue = make_venue("Saal", status=Venue.Status.RESEARCHED, consent_at=None)
        send_listing_request(venue)
        send_listing_request(venue)
        with self.assertRaises(ListingRequestError):
            send_listing_request(venue)
        self.assertEqual(len(mail.outbox), 2)

    def test_listed_venue_cannot_be_requested(self):
        with self.assertRaises(ListingRequestError):
            send_listing_request(make_venue())


class RetentionTests(TestCase):
    def test_cleanup(self):
        old = timezone.now() - timedelta(days=30)
        stale = User.objects.create_user(email="alt@example.org", password="x" * 12, is_active=False)
        User.objects.filter(pk=stale.pk).update(date_joined=old)
        fresh = User.objects.create_user(email="neu@example.org", password="x" * 12, is_active=False)
        sub = make_venue("Alt gemeldet", status=Venue.Status.UNCONFIRMED)
        Venue.objects.filter(pk=sub.pk).update(created_at=old)
        req_venue = make_venue("Angefragt", status=Venue.Status.RESEARCHED, consent_at=None)
        send_listing_request(req_venue)
        ListingRequest.objects.update(expires_at=old)
        Venue.objects.filter(pk=req_venue.pk).update(edit_token_expires_at=old)

        call_command("datenschutz_bereinigen", stdout=open("/dev/null", "w"))

        self.assertFalse(User.objects.filter(pk=stale.pk).exists())
        self.assertTrue(User.objects.filter(pk=fresh.pk).exists())
        self.assertFalse(Venue.objects.filter(pk=sub.pk).exists())
        req_venue.refresh_from_db()
        self.assertEqual(req_venue.status, Venue.Status.RESEARCHED)
        self.assertEqual(req_venue.edit_token_hash, "")


class ImportTests(TestCase):
    def test_osm_import_from_file(self):
        import json
        import tempfile

        data = {"elements": [
            {"type": "node", "id": 1, "lat": 50.94, "lon": 6.95, "tags": {
                "amenity": "community_centre", "name": "Bürgerzentrum Test", "addr:street": "Hauptstr.",
                "addr:housenumber": "5", "addr:suburb": "Kalk", "email": "info@bz.example", "phone": "0221 123", "wheelchair": "yes"}},
            {"type": "way", "id": 2, "center": {"lat": 50.9, "lon": 6.9}, "tags": {"amenity": "library"}},
        ]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(data, fh)
        call_command("import_osm", file=fh.name, stdout=open("/dev/null", "w"))
        call_command("import_osm", file=fh.name, stdout=open("/dev/null", "w"))  # idempotent
        venue = Venue.objects.get()
        self.assertEqual(venue.status, Venue.Status.RESEARCHED)
        self.assertEqual(venue.district, "kalk")
        self.assertEqual(venue.contact_phone, "")
        self.assertTrue(venue.step_free)


def request_data(**extra):
    from datetime import date

    data = {"occasion": "Hauskonzert", "date": (date.today() + timedelta(days=30)).isoformat(), "time_from": "19:00",
            "time_to": "22:00", "persons": "20", "message": "Wir sind ein Chor.", "reply_email": "chor@example.org",
            "privacy": "on"}
    data.update(extra)
    return data


def make_private(name="Wohnzimmer Müller", quarter="Ehrenfeld", capacity=30, **kwargs):
    venue = make_venue(
        name, visibility=Venue.Visibility.ON_REQUEST, public_title="Großes Wohnzimmer", operator_type="privat",
        quarter=quarter, street="Geheimweg 7", manager_email="gast@example.org", contact_email="gast@example.org", **kwargs,
    )
    Room.objects.create(venue=venue, name="Wohnzimmer", capacity=capacity, cost=Room.Cost.FREE)
    return venue


@override_settings(SITE_URL="http://testserver")
class PrivateListingTests(TestCase):
    def setUp(self):
        self.venue = make_private()
        self.user = make_group_user()
        self.client.force_login(self.user)

    def request_data(self, **extra):
        return request_data(**extra)

    def test_details_hidden_until_accepted(self):
        page = self.client.get(reverse("venues:search")).content.decode()
        self.assertIn("Großes Wohnzimmer", page)
        self.assertNotIn("Wohnzimmer Müller", page)
        self.assertNotIn("Geheimweg", page)
        detail = self.client.get(reverse("venues:detail", args=[self.venue.pk])).content.decode()
        self.assertNotIn("Geheimweg", detail)
        self.assertNotIn("gast@example.org", detail)

    def test_search_does_not_leak_name(self):
        response = self.client.get(reverse("venues:search"), {"q": "Müller"})
        self.assertEqual(response.context["total"], 0)
        self.assertEqual(self.client.get(reverse("venues:search"), {"q": "Wohnzimmer"}).context["total"], 1)

    def test_request_accept_grants_access(self):
        self.client.post(reverse("venues:detail", args=[self.venue.pk]), self.request_data())
        req = UsageRequest.objects.get()
        self.assertEqual(mail.outbox[-1].to, ["gast@example.org"])
        self.assertNotIn("Geheimweg", self.client.get(reverse("venues:detail", args=[self.venue.pk])).content.decode())
        path = extract_url(mail.outbox[-1].body).replace("http://testserver", "")
        self.assertContains(self.client.get(path), "Hauskonzert")
        self.client.post(path, {"action": "accept", "note": "Gern!"})
        req.refresh_from_db()
        self.assertEqual(req.status, UsageRequest.Status.ACCEPTED)
        self.assertEqual(mail.outbox[-1].to, ["chor@example.org"])
        self.assertContains(self.client.get(reverse("venues:detail", args=[self.venue.pk])), "Geheimweg")
        self.assertEqual(self.client.get(path).status_code, 404, "Link ist nach der Antwort verbraucht")

    def test_decline_keeps_details_hidden(self):
        self.client.post(reverse("venues:detail", args=[self.venue.pk]), self.request_data())
        path = extract_url(mail.outbox[-1].body).replace("http://testserver", "")
        self.client.post(path, {"action": "decline"})
        self.assertNotIn("Geheimweg", self.client.get(reverse("venues:detail", args=[self.venue.pk])).content.decode())

    def test_hidden_venue_not_on_map(self):
        Venue.objects.filter(pk=self.venue.pk).update(latitude=50.95, longitude=6.92)
        response = self.client.get(reverse("venues:search"))
        self.assertEqual(response.context["map_points"], [])

    def test_expired_request_notifies_group(self):
        self.client.post(reverse("venues:detail", args=[self.venue.pk]), self.request_data())
        UsageRequest.objects.update(expires_at=timezone.now() - timedelta(days=1))
        call_command("datenschutz_bereinigen", stdout=open("/dev/null", "w"))
        self.assertEqual(UsageRequest.objects.get().status, UsageRequest.Status.EXPIRED)
        self.assertEqual(mail.outbox[-1].to, ["chor@example.org"])

    def test_group_marked_acceptance_does_not_unlock_private_details(self):
        self.client.post(reverse("venues:detail", args=[self.venue.pk]), self.request_data())
        req = UsageRequest.objects.get()
        self.client.post(reverse("venues:request_action", args=[req.pk]), {"action": "zugesagt"})
        req.refresh_from_db()
        self.assertEqual(req.status, UsageRequest.Status.ACCEPTED)
        self.assertNotIn("Geheimweg", self.client.get(reverse("venues:detail", args=[self.venue.pk])).content.decode())


@override_settings(SITE_URL="http://testserver", FRESHNESS_INTERVAL_DAYS=180, FRESHNESS_REMINDER_DAYS=21, FRESHNESS_PAUSE_DAYS=42)
class FreshnessTests(TestCase):
    def test_check_reminder_pause_cycle(self):
        old = timezone.now() - timedelta(days=200)
        venue = make_venue(manager_email="haus@example.org", last_confirmed_at=old)
        now = timezone.now()
        self.assertEqual(run_freshness_checks(now)["abfragen"], 1)
        self.assertIn("noch aktuell", mail.outbox[-1].subject)
        self.assertEqual(run_freshness_checks(now)["abfragen"], 0, "nicht doppelt fragen")
        self.assertEqual(run_freshness_checks(now + timedelta(days=22))["erinnerungen"], 1)
        self.assertEqual(run_freshness_checks(now + timedelta(days=23))["erinnerungen"], 0)
        self.assertEqual(run_freshness_checks(now + timedelta(days=43))["pausiert"], 1)
        venue.refresh_from_db()
        self.assertEqual(venue.status, Venue.Status.PAUSED)
        # Ein Klick macht den Eintrag wieder sichtbar
        path = extract_url(mail.outbox[-1].body).replace("http://testserver", "")
        self.client.post(path, {"action": "still_current"})
        venue.refresh_from_db()
        self.assertEqual(venue.status, Venue.Status.LISTED)
        self.assertIsNone(venue.freshness_check_sent_at)

    def test_confirmation_resets_cycle(self):
        venue = make_venue(manager_email="haus@example.org", last_confirmed_at=timezone.now() - timedelta(days=200))
        run_freshness_checks()
        path = extract_url(mail.outbox[-1].body).replace("http://testserver", "")
        self.client.post(path, {"action": "still_current"})
        self.assertEqual(run_freshness_checks(timezone.now() + timedelta(days=50)), {"abfragen": 0, "erinnerungen": 0, "pausiert": 0})
        venue.refresh_from_db()
        self.assertEqual(venue.status, Venue.Status.LISTED)

    def test_public_source_not_asked(self):
        make_venue(status=Venue.Status.PUBLIC_SOURCE, manager_email="x@example.org", consent_at=None,
                   operator_type="oeffentlich", source_reference="https://example.org", last_confirmed_at=None)
        Venue.objects.update(created_at=timezone.now() - timedelta(days=400))
        self.assertEqual(run_freshness_checks()["abfragen"], 0)


class PublicSourceTests(TestCase):
    def test_visible_with_badge(self):
        venue = make_venue("Bürgerhaus X", status=Venue.Status.PUBLIC_SOURCE, consent_at=None, operator_type="oeffentlich",
                           source_reference="https://www.stadt-koeln.de/x")
        self.client.force_login(make_group_user())
        self.assertContains(self.client.get(reverse("venues:search")), "Noch nicht vom Ort bestätigt")
        self.assertContains(self.client.get(reverse("venues:detail", args=[venue.pk])), "https://www.stadt-koeln.de/x")

    def test_private_cannot_be_public_source(self):
        from django.core.exceptions import ValidationError

        venue = Venue(name="Privat", status=Venue.Status.PUBLIC_SOURCE, operator_type="privat", source_reference="x")
        with self.assertRaises(ValidationError):
            venue.clean()

    def test_import_real_data_file(self):
        call_command("orte_importieren", "data/orte_koeln.json", stdout=open("/dev/null", "w"))
        self.assertGreaterEqual(Venue.objects.listed().count(), 15)
        self.assertTrue(Venue.objects.filter(status=Venue.Status.RESEARCHED).exists())
        kalk = Venue.objects.get(name="Bürgerhaus Kalk")
        self.assertEqual(kalk.district, "kalk")
        self.assertEqual(kalk.rooms.count(), 2)
        call_command("orte_importieren", "data/orte_koeln.json", stdout=open("/dev/null", "w"))
        self.assertEqual(Venue.objects.filter(name="Bürgerhaus Kalk").count(), 1)

    @override_settings(SITE_URL="http://testserver")
    def test_consent_turns_public_source_into_listed(self):
        venue = make_venue("Bürgerhaus Y", status=Venue.Status.PUBLIC_SOURCE, consent_at=None, operator_type="oeffentlich",
                           source_reference="https://example.org")
        send_listing_request(venue)
        venue.refresh_from_db()
        self.assertEqual(venue.status, Venue.Status.PUBLIC_SOURCE, "bleibt während der Anfrage sichtbar")
        path = extract_url(mail.outbox[-1].body).replace("http://testserver", "")
        data = {
            "action": "save", "visibility": "oeffentlich", "name": "Bürgerhaus Y", "operator_type": "oeffentlich",
            "street": "Teststr. 1", "contact_email": "raum@example.org", "consent": "on",
            "rooms-TOTAL_FORMS": "1", "rooms-INITIAL_FORMS": "0", "rooms-MIN_NUM_FORMS": "1", "rooms-MAX_NUM_FORMS": "1000",
            "rooms-0-name": "Saal", "rooms-0-cost": "2", "rooms-0-rhythm": "beides",
        }
        self.client.post(path, data)
        venue.refresh_from_db()
        self.assertEqual(venue.status, Venue.Status.LISTED)


class AccessibilityTests(TestCase):
    """Grundlegende Prüfungen: Sprache, Überschrift, Beschriftungen, Sprunglink."""

    PUBLIC_PAGES = ["pages:home", "pages:help", "pages:help_groups", "pages:help_providers", "pages:faq", "pages:easy",
                    "pages:accessibility", "pages:privacy", "pages:imprint", "pages:terms", "venues:submit",
                    "accounts:register", "accounts:login"]

    def test_pages_have_structure(self):
        import re as _re

        for name in self.PUBLIC_PAGES:
            html = self.client.get(reverse(name)).content.decode()
            self.assertIn('<html lang="de">', html, name)
            self.assertEqual(len(_re.findall(r"<h1[ >]", html)), 1, f"{name}: genau eine h1")
            self.assertIn('href="#inhalt"', html, name)
            for field_id in _re.findall(r'<(?:input(?![^>]*type="hidden")|select|textarea)[^>]*\sid="([^"]+)"', html):
                if "website_url" in field_id or "__prefix__" in field_id:
                    continue
                self.assertTrue(
                    f'for="{field_id}"' in html or "aria-label=" in html.split(f'id="{field_id}"')[0][-300:],
                    f"{name}: Feld {field_id} ohne Beschriftung",
                )

    def test_error_summary_links_to_fields(self):
        html = self.client.post(reverse("accounts:register"), {"email": "", "name": ""}).content.decode()
        self.assertIn('id="fehler"', html)
        self.assertIn('href="#id_email"', html)
        self.assertIn('aria-invalid="true"', html)


@override_settings(SITE_URL="http://testserver", REQUEST_FROM_EMAIL="Raumanfragen <anfragen@example.org>")
class RequestRuleTests(TestCase):
    """Zentrale Absender-Adresse, eine Anfrage pro Termin, Reihenanfragen nacheinander."""

    def setUp(self):
        self.user = make_group_user()
        self.client.force_login(self.user)
        self.public = make_venue("Bürgerhaus A", contact_email="raum@a.example")
        self.public_b = make_venue("Bürgerhaus B", contact_email="raum@b.example")

    def post(self, venue, **extra):
        return self.client.post(reverse("venues:detail", args=[venue.pk]), request_data(**extra))

    def test_central_sender_with_reply_to_group(self):
        self.post(self.public, reply_email="vorstand@chor.example")
        msg = mail.outbox[-1]
        self.assertEqual(msg.from_email, "Raumanfragen <anfragen@example.org>")
        self.assertEqual(msg.to, ["raum@a.example"])
        self.assertEqual(msg.reply_to, ["vorstand@chor.example"])
        self.assertEqual(UsageRequest.objects.get().status, UsageRequest.Status.OPEN)

    def test_only_one_request_per_slot(self):
        self.post(self.public)
        response = self.post(self.public_b, time_from="21:00", time_to="23:00")
        self.assertContains(response, "Pro Termin ist nur eine Anfrage")
        self.assertEqual(UsageRequest.objects.count(), 1)
        # Anderer Zeitraum am selben Tag ist erlaubt
        self.post(self.public_b, time_from="10:00", time_to="12:00")
        self.assertEqual(UsageRequest.objects.count(), 2)

    def test_slot_free_after_decline_or_withdraw(self):
        self.post(self.public)
        first = UsageRequest.objects.get()
        self.client.post(reverse("venues:request_action", args=[first.pk]), {"action": "abgesagt"})
        self.post(self.public_b)
        second = UsageRequest.objects.get(venue=self.public_b)
        self.assertEqual(second.status, UsageRequest.Status.OPEN)
        self.client.post(reverse("venues:request_action", args=[second.pk]), {"action": "withdraw"})
        self.assertEqual(mail.outbox[-1].to, ["raum@b.example"], "Raumgeber erfährt vom Rückzug")
        self.post(self.public)
        self.assertEqual(UsageRequest.objects.filter(status=UsageRequest.Status.OPEN).count(), 1)

    def test_accepted_request_blocks_slot(self):
        self.post(self.public)
        path = extract_url(mail.outbox[-1].body).replace("http://testserver", "")
        self.client.logout()
        self.client.post(path, {"action": "accept"})
        self.client.force_login(self.user)
        self.assertContains(self.post(self.public_b), "Pro Termin ist nur eine Anfrage")

    def test_weekly_request_blocks_same_weekday_later(self):
        from datetime import date

        start = date.today() + timedelta(days=7)
        self.post(self.public, date=start.isoformat(), weekly="on")
        later = start + timedelta(days=21)
        self.assertContains(self.post(self.public_b, date=later.isoformat()), "Pro Termin ist nur eine Anfrage")
        other_day = start + timedelta(days=22)
        self.post(self.public_b, date=other_day.isoformat())
        self.assertEqual(UsageRequest.objects.count(), 2)

    def test_past_date_rejected(self):
        from datetime import date

        response = self.post(self.public, date=(date.today() - timedelta(days=1)).isoformat())
        self.assertContains(response, "Datum in der Zukunft")
        self.assertFalse(UsageRequest.objects.exists())

    def series(self, *venues, **extra):
        data = request_data(**extra)
        data["venues"] = [v.pk for v in venues]
        return self.client.post(f"{reverse('venues:series_request')}?district=ehrenfeld", data)

    def test_series_asks_one_after_another(self):
        c = make_private("Wohnzimmer C")
        self.series(self.public, self.public_b, c)
        items = list(UsageRequest.objects.order_by("queue_position"))
        self.assertEqual([i.status for i in items], ["offen", "eingereiht", "eingereiht"])
        self.assertEqual(len(mail.outbox), 1, "nur der erste Ort bekommt eine Anfrage")
        # Erster Ort sagt ab → zweiter wird angefragt
        path = extract_url(mail.outbox[-1].body).replace("http://testserver", "")
        self.client.post(path, {"action": "decline"})
        items = list(UsageRequest.objects.order_by("queue_position"))
        self.assertEqual([i.status for i in items], ["abgesagt", "offen", "eingereiht"])
        self.assertIn("raum@b.example", [m.to[0] for m in mail.outbox])
        # Zweiter Ort sagt zu → Rest entfällt, dritter bekommt nie eine Mail
        to_b = [m for m in mail.outbox if m.to == ["raum@b.example"]][-1]
        self.client.post(extract_url(to_b.body).replace("http://testserver", ""), {"action": "accept"})
        items = list(UsageRequest.objects.order_by("queue_position"))
        self.assertEqual([i.status for i in items], ["abgesagt", "zugesagt", "entfallen"])
        self.assertNotIn("gast@example.org", [m.to[0] for m in mail.outbox])

    def test_series_expiry_moves_on_and_ends(self):
        self.series(self.public, self.public_b)
        UsageRequest.objects.filter(status="offen").update(expires_at=timezone.now() - timedelta(days=1))
        expire_usage_requests()
        self.assertEqual(UsageRequest.objects.get(venue=self.public_b).status, UsageRequest.Status.OPEN)
        UsageRequest.objects.filter(status="offen").update(expires_at=timezone.now() - timedelta(days=1))
        expire_usage_requests()
        self.assertIn("beendet", mail.outbox[-1].subject)
        self.post(self.public)  # Termin wieder frei
        self.assertEqual(UsageRequest.objects.filter(status="offen").count(), 1)

    def test_series_blocked_by_existing_request_for_slot(self):
        self.post(self.public)
        self.assertContains(self.series(self.public_b), "Pro Termin ist nur eine Anfrage")

    def test_end_series(self):
        self.series(self.public, self.public_b)
        first = UsageRequest.objects.get(queue_position=1)
        self.client.post(reverse("venues:request_action", args=[first.pk]), {"action": "end_series"})
        self.assertEqual(set(UsageRequest.objects.values_list("status", flat=True)), {"zurueckgezogen", "entfallen"})
