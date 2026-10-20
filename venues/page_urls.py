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
    path("hilfe/", TemplateView.as_view(template_name="pages/help.html"), name="help"),
    path("hilfe/gruppen/", TemplateView.as_view(template_name="pages/help_groups.html"), name="help_groups"),
    path("hilfe/raumgeber/", TemplateView.as_view(template_name="pages/help_providers.html"), name="help_providers"),
    path("hilfe/fragen/", TemplateView.as_view(template_name="pages/faq.html"), name="faq"),
    path("einfache-sprache/", TemplateView.as_view(template_name="pages/easy.html"), name="easy"),
    path("barrierefreiheit/", TemplateView.as_view(template_name="pages/accessibility.html"), name="accessibility"),
]
