import json
import re

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import GroupProfile, User

REGISTRATION = {
    "email": "Chor@Example.org", "password1": "ein-langes-passwort-42", "password2": "ein-langes-passwort-42",
    "name": "Kölsche Stimmen", "kind": "chor", "purpose": "Wöchentliche Probe", "district": "",
    "not_private": "on", "terms": "on",
}


@override_settings(SITE_URL="http://testserver", GROUP_MANUAL_APPROVAL=False)
class RegistrationTests(TestCase):
    def verify_path(self):
        return re.search(r"http://testserver(\S+)", mail.outbox[-1].body).group(1)

    def test_register_verify_login(self):
        self.client.post(reverse("accounts:register"), REGISTRATION)
        user = User.objects.get(email="chor@example.org")
        self.assertFalse(user.is_active)
        path = self.verify_path()
        self.client.get(path)
        user.refresh_from_db()
        self.assertFalse(user.is_active, "Link-Vorschau darf nicht aktivieren")
        self.client.post(path)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(user.group_profile.status, GroupProfile.Status.APPROVED)
        self.assertTrue(user.password.startswith("argon2"))
        response = self.client.post(reverse("accounts:login"), {"username": "CHOR@example.org", "password": REGISTRATION["password1"]})
        self.assertRedirects(response, reverse("venues:search"))

    @override_settings(GROUP_MANUAL_APPROVAL=True, MODERATION_EMAILS=["verein@example.org"])
    def test_manual_approval_by_association(self):
        self.client.post(reverse("accounts:register"), REGISTRATION)
        self.client.post(self.verify_path())
        profile = User.objects.get().group_profile
        self.assertEqual(profile.status, GroupProfile.Status.PENDING)
        self.assertEqual(mail.outbox[-1].to, ["verein@example.org"])
        self.assertNotIn("chor@example.org", mail.outbox[-1].body, "Hinweis an den Verein ohne E-Mail der Gruppe")
        # Freischalten über die Verwaltung schickt der Gruppe eine E-Mail
        from accounts.admin import GroupProfileAdmin
        from django.contrib.admin.sites import site

        admin_obj = GroupProfileAdmin(GroupProfile, site)
        admin_obj.message_user = lambda *a, **k: None
        admin_obj.approve(None, GroupProfile.objects.all())
        profile.refresh_from_db()
        self.assertEqual(profile.status, GroupProfile.Status.APPROVED)
        self.assertEqual(mail.outbox[-1].to, ["chor@example.org"])

    def test_private_purpose_must_be_confirmed(self):
        data = dict(REGISTRATION)
        data.pop("not_private")
        self.client.post(reverse("accounts:register"), data)
        self.assertFalse(User.objects.exists())

    def test_export_and_delete(self):
        self.client.post(reverse("accounts:register"), REGISTRATION)
        self.client.post(self.verify_path())
        user = User.objects.get()
        self.client.force_login(user)
        data = json.loads(self.client.get(reverse("accounts:export")).content)
        self.assertEqual(data["gruppe"]["name"], "Kölsche Stimmen")
        self.client.post(reverse("accounts:delete"), {"password": "falsch"})
        self.assertTrue(User.objects.exists())
        self.client.post(reverse("accounts:delete"), {"password": REGISTRATION["password1"]})
        self.assertFalse(User.objects.exists())
        self.assertFalse(GroupProfile.objects.exists())
