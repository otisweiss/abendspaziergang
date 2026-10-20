from django.conf import settings


def site(request):
    group = None
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        group = getattr(user, "group_profile", None)
    return {
        "SITE_NAME": settings.SITE_NAME,
        "MAP_TILE_URL": settings.MAP_TILE_URL,
        "MAP_ATTRIBUTION": settings.MAP_ATTRIBUTION,
        "current_group": group,
        "can_search": bool(user and user.is_authenticated and user.can_search),
    }
