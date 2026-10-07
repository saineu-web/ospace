import logging
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET

from .forms import ContactForm, DriverApplyForm, RideRequestForm
from .models import Inquiry

log = logging.getLogger(__name__)

FAQ = [
    (_("How much can I earn?"), _("Drivers earn a minimum of $50 for every two rides, and many earn $150 or more per day by combining morning and afternoon school runs. You are paid per completed ride.")),
    (_("Do I need a special vehicle?"), _("No. Any four-door vehicle manufactured within the last 15 years, clean and in good working order, qualifies. You drive your own car.")),
    (_("What are the hours?"), _("School runs happen on weekday mornings (roughly 6–9 AM) and afternoons (roughly 2–5 PM). You choose which days and windows you are available inside the driver app.")),
    (_("Who hands the student over?"), _("A parent, guardian or teacher brings the student to and from the vehicle at each end of the ride. Drivers never enter homes or school buildings.")),
    (_("How long does approval take?"), _("Once your documents, background check and drug/TB test results are in, approval typically takes a few business days. Your portal shows exactly what is still pending.")),
    (_("Am I an employee?"), _("Ospace drivers are independent contractors. You keep full control of your schedule and drive when it suits you.")),
]

STEPS = [
    (_("Apply online"), _("Tell us about yourself and your vehicle. It takes two minutes.")),
    (_("Upload your documents"), _("Driver's license, insurance, registration and test results go into your secure driver portal.")),
    (_("Sign & get approved"), _("E-sign the driver agreements online. We review everything and confirm your approval.")),
    (_("Download the app & drive"), _("Install the ADROIT Driver app, set your availability and accept rides near you.")),
]

REQUIREMENTS = [
    (_("21+ years old"), _("with a valid U.S. driver's license")),
    (_("Four-door vehicle"), _("model year within the last 15 years")),
    (_("Background check"), _("we run it for you once you apply")),
    (_("Drug & TB test"), _("both screenings are required before approval")),
    (_("Clean driving record"), _("and current auto insurance in your name")),
    (_("Excited to drive with us"), _("reliable, friendly and great with kids")),
]

TESTIMONIALS = [
    {
        "name": "Ange",
        "role": _("Driver for 2+ years"),
        "quote": _("Wanting to be her own boss, driving with Ospace gave Ange the confidence to leave her job, follow her passion and start her own food business. Two years later, she still loves the flexibility it gives her."),
    },
    {
        "name": "Elijah",
        "role": _("The king of flexibility"),
        "quote": _("Elijah dedicates 95% of his time to CrossFit. The rest of the time he enjoys the freedom to earn extra income driving with Ospace."),
    },
    {
        "name": "Mariana",
        "role": _("Driver for 1.5 years"),
        "quote": _("Mariana has been driving with Ospace for one and a half years. A stay-at-home mom, she found an easy way to earn supplemental income during her free time."),
    },
]


def _deliver(inquiry: Inquiry):
    """Email the inquiry to the inbox. Never let a mail failure break the form."""
    lines = [f"{k.replace('_', ' ').title()}: {v}" for k, v in inquiry.extra.items() if v not in ("", None, False)]
    body = (
        f"New {inquiry.get_kind_display().lower()} from the website\n\n"
        f"Name: {inquiry.name}\nEmail: {inquiry.email}\nPhone: {inquiry.phone}\nCity: {inquiry.city}\n"
        + ("\n".join(lines) + "\n" if lines else "")
        + f"\nMessage:\n{inquiry.message or '-'}\n\n"
        f"Review in admin: {settings.SITE_URL}{reverse('admin:web_inquiry_change', args=[inquiry.pk])}\n"
    )
    try:
        send_mail(f"[Ospace] {inquiry.get_kind_display()} — {inquiry.name}", body, settings.DEFAULT_FROM_EMAIL, [settings.CONTACT_INBOX])
    except Exception:  # pragma: no cover
        log.exception("Could not email inquiry %s", inquiry.pk)


def home(request):
    return render(
        request,
        "web/home.html",
        {"steps": STEPS, "requirements": REQUIREMENTS, "testimonials": TESTIMONIALS, "faq": FAQ[:4], "apply_form": DriverApplyForm()},
    )


def drivers(request):
    form = DriverApplyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        inq = Inquiry.objects.create(
            kind="driver",
            name=form.full_name,
            email=d["email"],
            phone=d["phone"],
            city=d["city"],
            message=d["message"],
            extra={
                "first_name": d["first_name"],
                "last_name": d["last_name"],
                "vehicle_type": str(dict(form.fields["vehicle_type"].choices).get(d["vehicle_type"], d["vehicle_type"])),
                "vehicle_year": d["vehicle_year"],
                "over_21": d["over_21"],
                "language": request.LANGUAGE_CODE,
            },
        )
        _deliver(inq)
        request.session["applicant"] = {"first_name": d["first_name"], "last_name": d["last_name"], "email": d["email"], "phone": d["phone"]}
        return redirect(reverse("web:thanks") + "?next=portal")
    return render(
        request,
        "web/drivers.html",
        {"form": form, "steps": STEPS, "requirements": REQUIREMENTS, "faq": FAQ, "testimonials": TESTIMONIALS},
    )


def how_it_works(request):
    return render(request, "web/how_it_works.html", {"steps": STEPS})


def app(request):
    return render(request, "web/app.html")


def families(request):
    form = RideRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        inq = Inquiry.objects.create(
            kind="ride",
            name=d["name"],
            email=d["email"],
            phone=d["phone"],
            city=d["pickup_area"],
            message=d["message"],
            extra={"organisation": d["organisation"], "students": d["students"], "school": d["school"], "schedule": d["schedule"], "language": request.LANGUAGE_CODE},
        )
        _deliver(inq)
        return redirect("web:thanks")
    return render(request, "web/families.html", {"form": form})


def about(request):
    return render(request, "web/about.html", {"testimonials": TESTIMONIALS})


def media(request):
    return render(request, "web/media.html")


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        inq = Inquiry.objects.create(kind="contact", name=d["name"], email=d["email"], phone=d["phone"], message=d["message"], extra={"topic": d["topic"], "language": request.LANGUAGE_CODE})
        _deliver(inq)
        return redirect("web:thanks")
    return render(request, "web/contact.html", {"form": form})


def faq(request):
    return render(request, "web/faq.html", {"faq": FAQ})


def privacy(request):
    path = Path(__file__).with_name("privacy_policy.txt")
    paragraphs = [p for p in path.read_text(encoding="utf-8").split("\n\n") if p.strip()]
    return render(request, "web/privacy.html", {"paragraphs": paragraphs})


def thanks(request):
    return render(request, "web/thanks.html", {"next_portal": request.GET.get("next") == "portal"})


@require_GET
def robots(request):
    body = f"User-agent: *\nDisallow: /portal/\nDisallow: /*/portal/\nDisallow: /staff/\nDisallow: /admin/\nSitemap: {settings.SITE_URL}/sitemap.xml\n"
    return HttpResponse(body, content_type="text/plain")


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")
