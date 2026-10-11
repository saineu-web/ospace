"""Transactional mail for the portal. Every send is best-effort: a mail failure never breaks a request.

Driver-facing mail is rendered in the driver's preferred language (the language they applied in);
staff mail is always English.
"""
import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

log = logging.getLogger(__name__)


def _send(subject, template, ctx, to, lang="en"):
    ctx = {"SITE": settings.SITE, "SITE_URL": settings.SITE_URL, **ctx}
    try:
        with translation.override(lang or "en"):
            body = render_to_string(template, ctx)
            subject = str(subject)
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to])
    except Exception:  # pragma: no cover
        log.exception("Mail failed: %s -> %s", subject, to)


def _lang_prefix(lang):
    return "" if not lang or lang == "en" else f"/{lang}"


def set_password_link(driver):
    """One-time link (valid PASSWORD_RESET_TIMEOUT) that lets the driver choose a password."""
    uid = urlsafe_base64_encode(force_bytes(driver.user.pk))
    token = default_token_generator.make_token(driver.user)
    with translation.override(driver.language or "en"):
        path = reverse("portal:password_reset_confirm", kwargs={"uidb64": uid, "token": token})
    return settings.SITE_URL + path


def interested(driver):
    """New application from the website -> onboarding inbox."""
    _send(
        f"[Ospace] New driver interested — {driver.full_name}",
        "emails/staff_interested.txt",
        {"driver": driver, "url": settings.SITE_URL + reverse("staff:driver", args=[driver.pk])},
        settings.ONBOARDING_INBOX,
    )


def activated(driver):
    """Staff activated the profile -> driver gets the set-password / upload-documents link."""
    from django.utils.translation import gettext as _

    with translation.override(driver.language or "en"):
        subject = _("Your Ospace onboarding is open — upload your documents")
    _send(
        subject,
        "emails/activated.txt",
        {"driver": driver, "link": set_password_link(driver), "days": settings.PASSWORD_RESET_TIMEOUT // 86400},
        driver.email,
        lang=driver.language,
    )


def submitted(driver):
    from django.utils.translation import gettext as _

    with translation.override(driver.language or "en"):
        subject = _("We received your application")
    _send(subject, "emails/submitted.txt", {"driver": driver}, driver.email, lang=driver.language)
    _send(
        f"[Ospace] Driver application ready for review — {driver}",
        "emails/staff_submitted.txt",
        {"driver": driver, "url": settings.SITE_URL + reverse("staff:driver", args=[driver.pk])},
        settings.ONBOARDING_INBOX,
    )


def status_changed(driver):
    from django.utils.translation import gettext as _

    with translation.override(driver.language or "en"):
        subject = _("Your Ospace application: %(status)s") % {"status": driver.get_status_display()}
        url = settings.SITE_URL + reverse("portal:dashboard")
    _send(subject, "emails/status.txt", {"driver": driver, "url": url}, driver.email, lang=driver.language)


def document_rejected(document):
    from django.utils.translation import gettext as _

    driver = document.driver
    with translation.override(driver.language or "en"):
        subject = _("Please re-upload your %(name)s") % {"name": document.doc_type.name}
        url = settings.SITE_URL + reverse("portal:documents")
    _send(subject, "emails/document_rejected.txt", {"document": document, "driver": driver, "url": url}, driver.email, lang=driver.language)
