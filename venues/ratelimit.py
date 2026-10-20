"""Einfaches Rate-Limit ohne Speicherung von IP-Adressen.

Die IP wird mit dem geheimen Schlüssel und dem aktuellen Datum gehasht. Der Hash
liegt nur im Cache und verfällt nach dem Zeitfenster. So lässt sich weder die IP
zurückrechnen noch ein Verlauf über Tage hinweg bilden.
"""

import hashlib

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


def client_ip(request):
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "")


def is_limited(request, scope, limit, window_seconds=3600):
    """Zählt einen Versuch und gibt True zurück, wenn das Limit überschritten ist."""
    day = timezone.now().strftime("%Y-%m-%d")
    raw = f"{settings.SECRET_KEY}|{day}|{client_ip(request)}"
    key = f"rl:{scope}:{hashlib.sha256(raw.encode()).hexdigest()[:32]}"
    count = cache.get(key, 0) + 1
    cache.set(key, count, window_seconds)
    return count > limit
