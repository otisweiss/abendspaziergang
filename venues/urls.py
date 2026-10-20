from django.urls import path

from . import views

app_name = "venues"

urlpatterns = [
    path("suche/", views.search, name="search"),
    path("orte/<int:pk>/", views.detail, name="detail"),
    path("orte/<int:pk>/merken/", views.toggle_bookmark, name="bookmark"),
    path("merkliste/", views.bookmarks, name="bookmarks"),
    path("ort-melden/", views.submit, name="submit"),
    path("eintrag/link-anfordern/", views.request_link, name="request_link"),
    path("eintrag/<str:token>/", views.manage, name="manage"),
]
