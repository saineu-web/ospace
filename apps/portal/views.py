import base64
import mimetypes

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import emails
from .forms import DocumentUploadForm, ProfileForm, RegisterForm, SignForm
from .models import WEEKDAY_LABELS, WEEKDAYS, AgreementTemplate, DriverDocument, DriverProfile, SignedAgreement
from .pdf import build_agreement_pdf


def _driver(request) -> DriverProfile:
    try:
        return request.user.driver
    except DriverProfile.DoesNotExist:
        # Staff accounts have no driver profile; send them to their own dashboard.
        raise Http404


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return (xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")) or None


# ---------------------------------------------------------------- auth

def register(request):
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    initial = request.session.pop("applicant", None) or {}
    if initial.get("name") and " " in initial["name"]:
        first, last = initial["name"].split(" ", 1)
        initial.update(first_name=first, last_name=last)
    form = RegisterForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        user.driver.log("Account created")
        emails.welcome(user.driver)
        login(request, user)
        messages.success(request, "Welcome! Let's get your profile set up.")
        return redirect("portal:dashboard")
    return render(request, "portal/register.html", {"form": form})


class PortalLoginView(LoginView):
    template_name = "portal/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        u = self.request.user
        if u.is_staff and not DriverProfile.objects.filter(user=u).exists():
            return "/staff/"
        return super().get_success_url()


# ---------------------------------------------------------------- driver pages

@login_required
def dashboard(request):
    if request.user.is_staff and not DriverProfile.objects.filter(user=request.user).exists():
        return redirect("staff:index")
    d = _driver(request)
    return render(
        request,
        "portal/dashboard.html",
        {
            "driver": d,
            "docs": d.documents_summary(),
            "agreements": d.agreements_summary(),
            "missing": d.profile_missing(),
            "activity": d.activity.select_related("actor")[:8],
        },
    )


@login_required
def profile(request):
    d = _driver(request)
    form = ProfileForm(request.POST or None, instance=d)
    if request.method == "POST":
        form.read_availability(request.POST)
        if form.is_valid():
            form.save()
            d.log("Profile updated", actor=request.user)
            messages.success(request, "Profile saved.")
            return redirect("portal:dashboard" if not d.profile_missing() else "portal:profile")
    days = [(k, WEEKDAY_LABELS[k], form.availability.get(k, [])) for k in WEEKDAYS]
    return render(request, "portal/profile.html", {"driver": d, "form": form, "days": days})


@login_required
def documents(request):
    d = _driver(request)
    rows = d.document_rows()
    return render(request, "portal/documents.html", {"driver": d, "rows": rows, "form": DocumentUploadForm()})


@login_required
@require_POST
def upload_document(request, type_id):
    d = _driver(request)
    from .models import DocumentType

    dt = get_object_or_404(DocumentType, pk=type_id, active=True)
    form = DocumentUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        for err in form.errors.values():
            messages.error(request, err.as_text().lstrip("* "))
        return redirect("portal:documents")
    f = form.cleaned_data["file"]
    doc, created = DriverDocument.objects.get_or_create(driver=d, doc_type=dt, defaults={"original_name": f.name})
    if not created and doc.file:
        doc.file.delete(save=False)
    doc.file = f
    doc.original_name = f.name[:255]
    doc.size = f.size
    doc.content_type = f.content_type or mimetypes.guess_type(f.name)[0] or ""
    doc.expires_on = form.cleaned_data.get("expires_on") if dt.has_expiry else None
    doc.status = DriverDocument.STATUS_PENDING
    doc.review_note = ""
    doc.reviewed_at = None
    doc.reviewed_by = None
    doc.save()
    d.log("Document uploaded", actor=request.user, detail=dt.name)
    messages.success(request, f"{dt.name} uploaded. We'll review it shortly.")
    return redirect("portal:documents")


@login_required
@require_POST
def delete_document(request, pk):
    d = _driver(request)
    doc = get_object_or_404(DriverDocument, pk=pk, driver=d)
    if doc.status == DriverDocument.STATUS_APPROVED:
        messages.error(request, "Approved documents can't be removed. Contact us if it needs replacing.")
        return redirect("portal:documents")
    name = doc.doc_type.name
    doc.file.delete(save=False)
    doc.delete()
    d.log("Document removed", actor=request.user, detail=name)
    messages.info(request, f"{name} removed.")
    return redirect("portal:documents")


@login_required
def document_file(request, pk):
    """Serve a private upload to its owner or to staff. Never through /media/."""
    doc = get_object_or_404(DriverDocument, pk=pk)
    if not (request.user.is_staff or doc.driver.user_id == request.user.id):
        raise Http404
    resp = FileResponse(doc.file.open("rb"), content_type=doc.content_type or "application/octet-stream")
    disposition = "inline" if (doc.is_image or doc.content_type == "application/pdf") else "attachment"
    resp["Content-Disposition"] = f'{disposition}; filename="{doc.original_name}"'
    return resp


@login_required
def agreements(request):
    d = _driver(request)
    return render(request, "portal/agreements.html", {"driver": d, "rows": d.agreement_rows()})


@login_required
def sign(request, slug):
    d = _driver(request)
    t = get_object_or_404(AgreementTemplate, slug=slug, active=True)
    existing = d.agreements.filter(template=t, template_version=t.version).first()
    if existing:
        return redirect("portal:agreement_view", pk=existing.pk)
    body = t.render(d)
    form = SignForm(request.POST or None, initial={"typed_name": d.full_name})
    if request.method == "POST" and form.is_valid():
        typed = form.cleaned_data["typed_name"].strip()
        now = timezone.now()
        signed = SignedAgreement(
            driver=d,
            template=t,
            template_version=t.version,
            title=t.title,
            rendered_body=body,
            typed_name=typed,
            content_hash=SignedAgreement.hash_for(body, typed, now),
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
        )
        png = base64.b64decode(form.cleaned_data["signature"].split(",", 1)[1])
        signed.signature_image.save("signature.png", ContentFile(png), save=False)
        signed.save()
        signed.pdf.save(f"{t.slug}.pdf", ContentFile(build_agreement_pdf(signed)), save=True)
        d.log("Agreement signed", actor=request.user, detail=t.title)
        messages.success(request, f"{t.title} signed. A PDF copy is saved in your portal.")
        return redirect("portal:agreements")
    return render(request, "portal/sign.html", {"driver": d, "template": t, "body": body, "form": form})


@login_required
def agreement_view(request, pk):
    s = get_object_or_404(SignedAgreement, pk=pk)
    if not (request.user.is_staff or s.driver.user_id == request.user.id):
        raise Http404
    return render(request, "portal/agreement_view.html", {"driver": s.driver, "signed": s})


@login_required
def signature_image(request, pk):
    s = get_object_or_404(SignedAgreement, pk=pk)
    if not (request.user.is_staff or s.driver.user_id == request.user.id):
        raise Http404
    return FileResponse(s.signature_image.open("rb"), content_type="image/png")


@login_required
def agreement_pdf(request, pk):
    s = get_object_or_404(SignedAgreement, pk=pk)
    if not (request.user.is_staff or s.driver.user_id == request.user.id):
        raise Http404
    if not s.pdf:
        s.pdf.save(f"{s.template.slug}.pdf", ContentFile(build_agreement_pdf(s)), save=True)
    resp = FileResponse(s.pdf.open("rb"), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{s.template.slug}-{s.reference}.pdf"'
    return resp


@login_required
@require_POST
def submit_application(request):
    d = _driver(request)
    if not d.can_submit():
        messages.error(request, "Please finish every item on the checklist before submitting.")
        return redirect("portal:dashboard")
    d.status = DriverProfile.STATUS_SUBMITTED
    d.submitted_at = timezone.now()
    d.review_message = ""
    d.save(update_fields=["status", "submitted_at", "review_message", "updated_at"])
    d.log("Application submitted", actor=request.user)
    emails.submitted(d)
    messages.success(request, "Application submitted! We'll be in touch within a few business days.")
    return redirect("portal:dashboard")
