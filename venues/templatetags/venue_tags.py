from django import template

from venues.models import Room

register = template.Library()


@register.filter
def cost_label(value):
    if value is None:
        return ""
    return Room.Cost(value).label


@register.simple_tag
def page_url(querystring, number):
    return f"?{querystring}&seite={number}" if querystring else f"?seite={number}"


@register.filter
def district_name(label):
    """„4 – Ehrenfeld“ → „Ehrenfeld“."""
    return str(label).split("–", 1)[-1].strip() if label else ""
