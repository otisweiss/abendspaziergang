import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from venues.ratelimit import is_limited
from venues.services import notify_moderation, send_templated_mail

from .forms import DeleteAccountForm, EmailAuthenticationForm, GroupProfileForm, RegistrationForm
from .models import GroupProfile, User


def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST":
        if is_limited(request, "register", limit=5):
            messages.error(request, "Zu viele Registrierungen in kurzer Zeit. Bitte versuche es später erneut.")
        elif form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    email=form.cleaned_data["email"], password=form.cleaned_data["password1"], is_active=False
                )
                profile = form.save(commit=False)
                profile.user = user
                profile.terms_accepted_at = timezone.now()
                profile.save()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            url = settings.SITE_URL + reverse("accounts:verify", args=[uid, token])
            send_templated_mail("verify_account", user.email, {"url": url, "group": profile})
            return render(request, "accounts/register_done.html", {"email": user.email})
    return render(request, "accounts/register.html", {"form": form})


def verify(request, uidb64, token):
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None
    if user is None or not default_token_generator.check_token(user, token):
        return render(request, "accounts/verify_invalid.html", status=400)
    # Bestätigung per POST, damit Link-Vorschauen in Mailprogrammen das Konto nicht aktivieren.
    if request.method != "POST":
        return render(request, "accounts/verify.html")
    user.is_active = True
    user.save(update_fields=["is_active"])
    profile = user.group_profile
    if not settings.GROUP_MANUAL_APPROVAL and profile.status == GroupProfile.Status.PENDING:
        profile.status = GroupProfile.Status.APPROVED
        profile.save(update_fields=["status"])
        messages.success(request, "Dein Konto ist bestätigt. Du kannst dich jetzt anmelden.")
    else:
        notify_moderation("Neue Gruppe wartet auf Freischaltung", f"Neue Registrierung: {profile.name}")
        messages.success(
            request,
            f"Deine E-Mail-Adresse ist bestätigt. {settings.OPERATOR_NAME} prüft jetzt eure Angaben. "
            "Wir schreiben dir, sobald ihr suchen könnt.",
        )
    return redirect("accounts:login")


class LoginView(auth_views.LoginView):
    form_class = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        if is_limited(request, "login", limit=10, window_seconds=900):
            messages.error(request, "Zu viele Anmeldeversuche. Bitte warte 15 Minuten.")
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)


class PasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "emails/password_reset.txt"
    subject_template_name = "emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    extra_email_context = {"SITE_NAME": settings.SITE_NAME}

    def post(self, request, *args, **kwargs):
        if is_limited(request, "password_reset", limit=5):
            messages.error(request, "Zu viele Anfragen. Bitte versuche es später erneut.")
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        form.cleaned_data["email"] = form.cleaned_data["email"].lower()
        return super().form_valid(form)


@login_required
def account(request):
    profile = getattr(request.user, "group_profile", None)
    form = GroupProfileForm(request.POST or None, instance=profile) if profile else None
    if form is not None and request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Gespeichert.")
        return redirect("accounts:account")
    return render(request, "accounts/account.html", {"form": form, "profile": profile})


@login_required
def export(request):
    """Auskunft und Datenübertragbarkeit (Art. 15 und 20 DSGVO) als JSON-Datei."""
    user = request.user
    profile = getattr(user, "group_profile", None)
    data = {
        "konto": {
            "email": user.email,
            "registriert_am": user.date_joined.isoformat(),
            "letzte_anmeldung": user.last_login.isoformat() if user.last_login else None,
        },
        "gruppe": None,
        "merkliste": [
            {"ort": b.venue.name, "gemerkt_am": b.created_at.isoformat()}
            for b in user.bookmarks.select_related("venue")
        ],
    }
    if profile:
        data["gruppe"] = {
            "name": profile.name,
            "art": profile.get_kind_display(),
            "zweck": profile.purpose,
            "stadtbezirk": profile.get_district_display(),
            "status": profile.get_status_display(),
            "nutzungsbedingungen_akzeptiert_am": profile.terms_accepted_at.isoformat(),
        }
    response = HttpResponse(json.dumps(data, ensure_ascii=False, indent=2), content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="meine-daten.json"'
    return response


@login_required
def delete_account(request):
    form = DeleteAccountForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Dein Konto und alle zugehörigen Daten sind gelöscht.")
        return redirect("pages:home")
    return render(request, "accounts/delete.html", {"form": form})
