from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from venues.koeln import DISTRICTS


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("E-Mail-Adresse fehlt")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """Benutzerkonto. Anmeldung mit E-Mail, kein Benutzername, keine Klarnamenpflicht."""

    username = None
    first_name = None
    last_name = None
    email = models.EmailField("E-Mail-Adresse", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "Benutzerkonto"
        verbose_name_plural = "Benutzerkonten"

    def __str__(self):
        return self.email

    @property
    def can_search(self):
        if not self.is_active:
            return False
        if self.is_staff:
            return True
        profile = getattr(self, "group_profile", None)
        return profile is not None and profile.status == GroupProfile.Status.APPROVED


class GroupProfile(models.Model):
    class Kind(models.TextChoices):
        ASSOCIATION = "verein", "Verein (e.V. oder nicht eingetragen)"
        CHOIR = "chor", "Chor, Ensemble, Musikgruppe"
        INITIATIVE = "initiative", "Initiative, Nachbarschaftsgruppe"
        SELF_HELP = "selbsthilfe", "Selbsthilfegruppe"
        REGULARS = "stammtisch", "Stammtisch, Interessengruppe"
        NONPROFIT = "traeger", "Gemeinnütziger Träger, Stiftung"
        OTHER = "sonstige", "Sonstige nicht kommerzielle Gruppe"

    class Status(models.TextChoices):
        PENDING = "offen", "Wartet auf Freischaltung"
        APPROVED = "frei", "Freigeschaltet"
        BLOCKED = "gesperrt", "Gesperrt"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="group_profile")
    name = models.CharField("Name der Gruppe", max_length=150)
    kind = models.CharField("Art der Gruppe", max_length=20, choices=Kind.choices)
    purpose = models.TextField(
        "Wofür sucht ihr Räume?",
        max_length=600,
        help_text="Kurz und ohne Namen von Personen, z. B. „wöchentliche Chorprobe, ca. 25 Personen“.",
    )
    district = models.CharField("Stadtbezirk (optional)", max_length=20, blank=True, choices=DISTRICTS)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    terms_accepted_at = models.DateTimeField("Nutzungsbedingungen akzeptiert am")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Gruppe"
        verbose_name_plural = "Gruppen"

    def __str__(self):
        return self.name
