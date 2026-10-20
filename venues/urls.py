from django.urls import path

from . import views

app_name = "venues"

urlpatterns = [
    path("suche/", views.search, name="search"),
    path("orte/<int:pk>/", views.detail, name="detail"),
    path("orte/<int:pk>/merken/", views.toggle_bookmark, name="bookmark"),
    path("merkliste/", views.bookmarks, name="bookmarks"),
    path("anfragen/", views.my_requests, name="my_requests"),
    path("anfragen/reihenanfrage/", views.series_request, name="series_request"),
    path("anfragen/<int:pk>/aktion/", views.request_action, name="request_action"),
    path("anfrage/<str:token>/", views.respond, name="respond"),
    path("ort-melden/", views.submit, name="submit"),
    path("eintrag/link-anfordern/", views.request_link, name="request_link"),
    path("eintrag/<str:token>/", views.manage, name="manage"),
]
