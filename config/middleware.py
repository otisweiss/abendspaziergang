from django.conf import settings


class SecurityHeadersMiddleware:
    """Setzt eine strenge Content-Security-Policy und weitere Schutz-Header.

    Es werden keine Skripte, Schriften oder Styles von Dritten geladen. Einzige
    Ausnahme sind Kartenkacheln, und auch die erst nach einem Klick.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        tiles = settings.MAP_TILE_ORIGIN
        self.csp = "; ".join(
            [
                "default-src 'self'",
                "script-src 'self'",
                "style-src 'self'",
                f"img-src 'self' data: {tiles}",
                "font-src 'self'",
                "connect-src 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "object-src 'none'",
            ]
        )

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/verwaltung/"):
            # Die Django-Verwaltung nutzt Inline-Skripte; dort nur die Grundregeln.
            response.setdefault("Content-Security-Policy", "frame-ancestors 'none'; object-src 'none'")
        else:
            response.setdefault("Content-Security-Policy", self.csp)
        response.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=(), interest-cohort=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response
