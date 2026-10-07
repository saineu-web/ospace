from django import template
from django.urls import translate_url
from django.utils import translation

register = template.Library()


@register.simple_tag(takes_context=True)
def switch_lang_url(context, lang_code):
    """Same page in another language: /drivers/ -> /es/drivers/ (English has no prefix)."""
    request = context.get("request")
    path = request.get_full_path() if request else "/"
    return translate_url(path, lang_code)


@register.simple_tag
def current_lang():
    return translation.get_language() or "en"


@register.simple_tag
def text_dir():
    return "rtl" if translation.get_language_bidi() else "ltr"
