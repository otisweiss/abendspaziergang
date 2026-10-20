from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Veedelsräume – Redaktion"
admin.site.site_title = "Veedelsräume"
admin.site.index_title = "Verwaltung"

urlpatterns = [
    path("verwaltung/", admin.site.urls),
    path("konto/", include("accounts.urls")),
    path("", include("venues.page_urls")),
    path("", include("venues.urls")),
]
