from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path("ueber/", TemplateView.as_view(template_name="pages/about.html"), name="about"),
    path("datenschutz/", TemplateView.as_view(template_name="pages/privacy.html"), name="privacy"),
    path("impressum/", TemplateView.as_view(template_name="pages/imprint.html"), name="imprint"),
    path("nutzungsbedingungen/", TemplateView.as_view(template_name="pages/terms.html"), name="terms"),
]
