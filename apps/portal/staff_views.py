"""Staff review desk: a focused UI on top of the same models the admin exposes."""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import emails
from .forms import ReviewDocumentForm, ReviewDriverForm
from .models import DriverDocument, DriverProfile

# What needs a human first: fresh applications, then submissions waiting for a decision.
ORDER = {
    DriverProfile.STATUS_INTERESTED: 0,
    DriverProfile.STATUS_SUBMITTED: 1,
    DriverProfile.STATUS_CHANGES: 2,
    DriverProfile.STATUS_IN_PROGRESS: 3,
}


@staff_member_required
def index(request):
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    qs = DriverProfile.objects.select_related("user").annotate(
        n_docs=Count("documents", distinct=True),
        n_pending=Count("documents", filter=Q(documents__status=DriverDocument.STATUS_PENDING), distinct=True),
        n_signed=Count("agreements", distinct=True),
    )
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__email__icontains=q) | Q(phone__icontains=q))
    drivers = sorted(qs, key=lambda d: (ORDER.get(d.status, 9), -d.created_at.timestamp()))
    counts = dict(DriverProfile.objects.values_list("status").annotate(c=Count("id")))
    tiles = [(code, label, counts.get(code, 0)) for code, label in DriverProfile.STATUS_CHOICES]
    return render(request, "staff/index.html", {"drivers": drivers, "tiles": tiles, "status": status, "q": q, "total": sum(counts.values())})


@staff_member_required
def driver(request, pk):
    d = get_object_or_404(DriverProfile.objects.select_related("user"), pk=pk)
    form = ReviewDriverForm(initial={"status": d.status, "review_message": d.review_message, "internal_notes": d.internal_notes})
    return render(
        request,
        "staff/driver.html",
        {
            "driver": d,
            "form": form,
            "doc_rows": d.document_rows(),
            "agreement_rows": d.agreement_rows(),
            "activity": d.activity.select_related("actor")[:30],
            "doc_statuses": DriverDocument.STATUS_CHOICES,
        },
    )


@staff_member_required
@require_POST
def activate_driver(request, pk):
    """Interested -> In progress. Emails the driver a set-password link that lands on their documents."""
    d = get_object_or_404(DriverProfile, pk=pk)
    if d.status != DriverProfile.STATUS_INTERESTED:
        messages.error(request, "Only an Interested profile can be activated.")
        return redirect("staff:driver", pk=pk)
    d.status = DriverProfile.STATUS_IN_PROGRESS
    d.activated_at = timezone.now()
    d.activated_by = request.user
    d.save(update_fields=["status", "activated_at", "activated_by", "updated_at"])
    d.log("Activated — documents requested", actor=request.user)
    emails.activated(d)
    messages.success(request, f"{d} activated. They've been emailed a link to set a password and upload documents.")
    return redirect("staff:driver", pk=pk)


@staff_member_required
@require_POST
def delete_driver(request, pk):
    """Permanent delete: profile, login, uploads, signatures and PDFs. No undo."""
    d = get_object_or_404(DriverProfile, pk=pk)
    name = str(d)
    d.delete_with_files()
    messages.success(request, f"{name} deleted permanently.")
    return redirect("staff:index")


@staff_member_required
@require_POST
def review_document(request, pk):
    doc = get_object_or_404(DriverDocument.objects.select_related("driver", "doc_type"), pk=pk)
    form = ReviewDocumentForm(request.POST)
    if form.is_valid():
        doc.status = form.cleaned_data["status"]
        doc.review_note = form.cleaned_data["review_note"]
        doc.reviewed_at = timezone.now()
        doc.reviewed_by = request.user
        doc.save()
        doc.driver.log(f"Document {doc.get_status_display().lower()}", actor=request.user, detail=f"{doc.doc_type.name}: {doc.review_note}".strip(": "))
        if doc.status == DriverDocument.STATUS_REJECTED:
            emails.document_rejected(doc)
        messages.success(request, f"{doc.doc_type.name}: {doc.get_status_display()}.")
    return redirect("staff:driver", pk=doc.driver_id)


@staff_member_required
@require_POST
def review_driver(request, pk):
    d = get_object_or_404(DriverProfile, pk=pk)
    form = ReviewDriverForm(request.POST)
    if form.is_valid():
        old = d.status
        new = form.cleaned_data["status"]
        if old == DriverProfile.STATUS_INTERESTED and new != old:
            messages.error(request, "Use the Activate button for an Interested profile, so the driver gets their access link.")
            return redirect("staff:driver", pk=pk)
        d.status = new
        d.review_message = form.cleaned_data["review_message"]
        d.internal_notes = form.cleaned_data["internal_notes"]
        if d.status != old:
            d.reviewed_at = timezone.now()
            d.reviewed_by = request.user
            d.log(f"Status → {d.get_status_display()}", actor=request.user, detail=d.review_message[:300])
            emails.status_changed(d)
        d.save()
        messages.success(request, "Saved.")
    return redirect("staff:driver", pk=pk)
