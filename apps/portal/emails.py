"""Transactional mail for the portal. Every send is best-effort: a mail failure never breaks a request."""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

log = logging.getLogger(__name__)


def _send(subject, template, ctx, to):
    ctx = {"SITE": settings.SITE, "SITE_URL": settings.SITE_URL, **ctx}
    try:
        send_mail(subject, render_to_string(template, ctx), settings.DEFAULT_FROM_EMAIL, [to])
    except Exception:  # pragma: no cover
        log.exception("Mail failed: %s -> %s", subject, to)


def welcome(driver):
    _send("Welcome to the Ospace driver portal", "emails/welcome.txt", {"driver": driver, "url": settings.SITE_URL + reverse("portal:dashboard")}, driver.email)


def submitted(driver):
    _send("We received your application", "emails/submitted.txt", {"driver": driver}, driver.email)
    _send(
        f"[Ospace] Driver application ready for review — {driver}",
        "emails/staff_submitted.txt",
        {"driver": driver, "url": settings.SITE_URL + reverse("staff:driver", args=[driver.pk])},
        settings.CONTACT_INBOX,
    )


def status_changed(driver):
    _send(
        f"Your Ospace application: {driver.get_status_display()}",
        "emails/status.txt",
        {"driver": driver, "url": settings.SITE_URL + reverse("portal:dashboard")},
        driver.email,
    )


def document_rejected(document):
    _send(
        f"Please re-upload your {document.doc_type.name}",
        "emails/document_rejected.txt",
        {"document": document, "driver": document.driver, "url": settings.SITE_URL + reverse("portal:documents")},
        document.driver.email,
    )
