import re
from datetime import timedelta

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import GroupProfile, User

from .models import Equipment, ListingRequest, Purpose, Room, TimeSlot, Venue
from .search import search_venues
from .services import ListingRequestError, send_listing_request


def make_group_user(email="chor@example.org", status=GroupProfile.Status.APPROVED):
    user = User.objects.create_user(email=email, password="sehr-geheimes-passwort")
    GroupProfile.objects.create(user=user, name="Testchor", kind="chor", purpose="Probe", status=status, terms_accepted_at=timezone.now())
    return user


def make_venue(name="Bürgerhaus", status=Venue.Status.LISTED, **kwargs):
    defaults = dict(street="Teststr. 1", quarter="Ehrenfeld", contact_email="raum@example.org", consent_at=timezone.now())
    defaults.update(kwargs)
    return Venue.objects.create(name=name, status=status, **defaults)


def extract_url(body):
    return re.search(r"https?://\S+", body).group(0)


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
            "name": "Vereinsheim Test", "operator": "TV e.V.", "operator_type": "gemeinnuetzig", "street": "Weg 2",
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
        self.assertContains(response, "bisher nirgends sichtbar")
        data = {
            "action": "save", "name": "Bibliothek", "operator_type": "oeffentlich", "street": "Teststr. 1",
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
