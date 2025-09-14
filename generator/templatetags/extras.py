from django import template

register = template.Library()


@register.filter(name="trim")
def trim_filter(value):
    """Supprime les espaces début/fin (équivalent simple de trim)."""
    if value is None:
        return ""
    return str(value).strip()


