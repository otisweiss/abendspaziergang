from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from venues.forms import HoneypotMixin

from .models import GroupProfile, User


class RegistrationForm(HoneypotMixin, forms.ModelForm):
    email = forms.EmailField(label="E-Mail-Adresse", help_text="Gern eine Adresse der Gruppe, nicht zwingend eine private.")
    password1 = forms.CharField(label="Passwort", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Passwort wiederholen", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    not_private = forms.BooleanField(
        label="Wir suchen Räume für gemeinschaftliche oder soziale Zwecke, nicht für rein private Feiern "
        "(z. B. Geburtstage oder Hochzeiten)."
    )
    terms = forms.BooleanField(label="Ich akzeptiere die Nutzungsbedingungen und habe die Datenschutzhinweise gelesen.")

    class Meta:
        model = GroupProfile
        fields = ["name", "kind", "purpose", "district"]
        widgets = {"purpose": forms.Textarea(attrs={"rows": 3})}

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            # Bewusst allgemein formuliert. Eine Bestätigungsmail an bestehende Konten
            # geht nicht raus, um niemanden mit Mails zu überschwemmen.
            raise forms.ValidationError("Mit dieser Adresse ist eine Registrierung nicht möglich. Passwort vergessen?")
        return email

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Die Passwörter stimmen nicht überein.")
        elif p1:
            try:
                password_validation.validate_password(p1, User(email=data.get("email", "")))
            except forms.ValidationError as exc:
                self.add_error("password1", exc)
        return data


class GroupProfileForm(forms.ModelForm):
    class Meta:
        model = GroupProfile
        fields = ["name", "kind", "purpose", "district"]
        widgets = {"purpose": forms.Textarea(attrs={"rows": 3})}


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="E-Mail-Adresse", widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}))

    def clean_username(self):
        return self.cleaned_data["username"].lower()


class DeleteAccountForm(forms.Form):
    password = forms.CharField(label="Zur Bestätigung dein Passwort", widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        if not self.user.check_password(self.cleaned_data["password"]):
            raise forms.ValidationError("Das Passwort stimmt nicht.")
        return ""
