import hashlib
import os
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone

# Driver uploads (licenses, insurance, signed agreements) never live under MEDIA_ROOT.
# They are served only through views that check ownership — see views.document_file.
private_storage = FileSystemStorage(location=str(settings.PRIVATE_ROOT), base_url=None)

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]
WEEKDAY_LABELS = {"mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday", "fri": "Friday"}
US_STATES = [
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"), ("CA", "California"), ("CO", "Colorado"),
    ("CT", "Connecticut"), ("DE", "Delaware"), ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"), ("ID", "Idaho"),
    ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"), ("KS", "Kansas"), ("KY", "Kentucky"), ("LA", "Louisiana"),
    ("ME", "Maine"), ("MD", "Maryland"), ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"),
    ("MS", "Mississippi"), ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"), ("NV", "Nevada"),
    ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"), ("NY", "New York"), ("NC", "North Carolina"),
    ("ND", "North Dakota"), ("OH", "Ohio"), ("OK", "Oklahoma"), ("OR", "Oregon"), ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"), ("SC", "South Carolina"), ("SD", "South Dakota"), ("TN", "Tennessee"), ("TX", "Texas"),
    ("UT", "Utah"), ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"), ("WV", "West Virginia"),
    ("WI", "Wisconsin"), ("WY", "Wyoming"), ("DC", "Washington DC"),
]


def _upload_path(prefix, instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"{prefix}/{instance.driver_id}/{uuid.uuid4().hex}{ext}"


def document_upload_path(instance, filename):
    return _upload_path("documents", instance, filename)


def signature_upload_path(instance, filename):
    return _upload_path("signatures", instance, filename)


def agreement_pdf_path(instance, filename):
    return _upload_path("agreements", instance, filename)


class DriverProfile(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_CHANGES = "changes_requested"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Getting started"),
        (STATUS_SUBMITTED, "Under review"),
        (STATUS_CHANGES, "Changes requested"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Not approved"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="driver")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)

    # Personal
    phone = models.CharField(max_length=40)
    date_of_birth = models.DateField(null=True, blank=True)
    address1 = models.CharField("Street address", max_length=200, blank=True)
    address2 = models.CharField("Apt / unit", max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, choices=US_STATES, default="TX", blank=True)
    zip_code = models.CharField("ZIP", max_length=12, blank=True)

    # Driver's license
    license_number = models.CharField(max_length=40, blank=True)
    license_state = models.CharField(max_length=2, choices=US_STATES, default="TX", blank=True)
    license_expiry = models.DateField(null=True, blank=True)

    # Vehicle
    vehicle_year = models.PositiveIntegerField(null=True, blank=True)
    vehicle_make = models.CharField(max_length=60, blank=True)
    vehicle_model = models.CharField(max_length=60, blank=True)
    vehicle_color = models.CharField(max_length=40, blank=True)
    vehicle_plate = models.CharField("License plate", max_length=20, blank=True)
    vehicle_seats = models.PositiveSmallIntegerField("Passenger seats", null=True, blank=True)

    # Insurance
    insurance_provider = models.CharField(max_length=100, blank=True)
    insurance_policy = models.CharField("Policy number", max_length=60, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)

    # Emergency contact
    emergency_name = models.CharField(max_length=120, blank=True)
    emergency_phone = models.CharField(max_length=40, blank=True)
    emergency_relationship = models.CharField(max_length=60, blank=True)

    # Availability: {"mon": ["am", "pm"], ...}
    availability = models.JSONField(default=dict, blank=True)
    how_heard = models.CharField("How did you hear about us?", max_length=120, blank=True)

    # Review
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    review_message = models.TextField(blank=True, help_text="Shown to the driver on their dashboard.")
    internal_notes = models.TextField(blank=True, help_text="Staff only.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.full_name or self.user.email

    # -- convenience -------------------------------------------------------
    @property
    def full_name(self):
        return self.user.get_full_name().strip()

    @property
    def email(self):
        return self.user.email

    PROFILE_REQUIRED = [
        "phone", "date_of_birth", "address1", "city", "state", "zip_code",
        "license_number", "license_state", "license_expiry",
        "vehicle_year", "vehicle_make", "vehicle_model", "vehicle_color", "vehicle_plate",
        "insurance_provider", "insurance_policy", "insurance_expiry",
        "emergency_name", "emergency_phone",
    ]

    def profile_missing(self):
        missing = [f for f in self.PROFILE_REQUIRED if not getattr(self, f)]
        if not self.availability or not any(self.availability.values()):
            missing.append("availability")
        return missing

    def profile_pct(self):
        total = len(self.PROFILE_REQUIRED) + 1
        return int(round(100 * (total - len(self.profile_missing())) / total))

    def document_rows(self):
        """One row per active DocumentType, with the driver's current upload if any."""
        docs = {d.doc_type_id: d for d in self.documents.select_related("doc_type")}
        return [(t, docs.get(t.id)) for t in DocumentType.objects.filter(active=True)]

    def documents_summary(self):
        rows = self.document_rows()
        req = [(t, d) for t, d in rows if t.required]
        uploaded = sum(1 for t, d in req if d)
        approved = sum(1 for t, d in req if d and d.status == DriverDocument.STATUS_APPROVED)
        rejected = sum(1 for t, d in req if d and d.status == DriverDocument.STATUS_REJECTED)
        return {"required": len(req), "uploaded": uploaded, "approved": approved, "rejected": rejected}

    def agreement_rows(self):
        signed = {}
        for s in self.agreements.select_related("template").order_by("signed_at"):
            signed[s.template_id] = s  # latest wins
        rows = []
        for t in AgreementTemplate.objects.filter(active=True):
            s = signed.get(t.id)
            current = s if (s and s.template_version == t.version) else None
            rows.append((t, current, s))
        return rows

    def agreements_summary(self):
        rows = self.agreement_rows()
        req = [(t, c) for t, c, _ in rows if t.required]
        return {"required": len(req), "signed": sum(1 for t, c in req if c)}

    def can_submit(self):
        d = self.documents_summary()
        a = self.agreements_summary()
        return (
            self.status in (self.STATUS_DRAFT, self.STATUS_CHANGES)
            and not self.profile_missing()
            and d["uploaded"] == d["required"]
            and d["rejected"] == 0
            and a["signed"] == a["required"]
        )

    def overall_pct(self):
        d = self.documents_summary()
        a = self.agreements_summary()
        parts = [self.profile_pct()]
        parts.append(100 if not d["required"] else int(100 * d["uploaded"] / d["required"]))
        parts.append(100 if not a["required"] else int(100 * a["signed"] / a["required"]))
        return int(sum(parts) / len(parts))

    def availability_label(self):
        out = []
        for day in WEEKDAYS:
            slots = self.availability.get(day) or []
            if slots:
                out.append(f"{WEEKDAY_LABELS[day][:3]} {'/'.join(s.upper() for s in slots)}")
        return ", ".join(out) or "—"

    def log(self, action, actor=None, detail=""):
        ActivityLog.objects.create(driver=self, actor=actor, action=action, detail=detail)


class DocumentType(models.Model):
    """Configured by staff in /admin — add, rename or retire document requirements without code."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=300, blank=True, help_text="Tell the driver what to upload, e.g. 'Front and back, all corners visible'.")
    required = models.BooleanField(default=True)
    has_expiry = models.BooleanField(default=False, help_text="Ask the driver for an expiry date (license, insurance...).")
    sort_order = models.PositiveSmallIntegerField(default=10)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class DriverDocument(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [(STATUS_PENDING, "Pending review"), (STATUS_APPROVED, "Approved"), (STATUS_REJECTED, "Needs re-upload")]

    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT, related_name="documents")
    file = models.FileField(upload_to=document_upload_path, storage=private_storage)
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    review_note = models.CharField(max_length=300, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("driver", "doc_type")]
        ordering = ["doc_type__sort_order"]

    def __str__(self):
        return f"{self.doc_type} — {self.driver}"

    @property
    def is_image(self):
        return self.content_type.startswith("image/")

    @property
    def is_expired(self):
        return bool(self.expires_on and self.expires_on < timezone.localdate())


class AgreementTemplate(models.Model):
    """A document the driver must e-sign. Body is plain text with blank lines between paragraphs.

    Placeholders: {{driver_name}}, {{driver_email}}, {{driver_phone}}, {{date}}, {{company}},
    {{vehicle}}. Bump `version` after editing the text — drivers who signed the old text are
    asked to sign again.
    """

    title = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    summary = models.CharField(max_length=300, blank=True, help_text="One line shown in the driver's checklist.")
    body = models.TextField()
    version = models.PositiveSmallIntegerField(default=1)
    required = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=10)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self):
        return f"{self.title} (v{self.version})"

    def render(self, driver: DriverProfile) -> str:
        vehicle = " ".join(str(x) for x in (driver.vehicle_year, driver.vehicle_make, driver.vehicle_model) if x) or "—"
        ctx = {
            "driver_name": driver.full_name or driver.email,
            "driver_email": driver.email,
            "driver_phone": driver.phone or "—",
            "date": timezone.localdate().strftime("%B %d, %Y"),
            "company": settings.SITE["legal_name"],
            "vehicle": vehicle,
        }
        text = self.body
        for k, v in ctx.items():
            text = text.replace("{{" + k + "}}", str(v))
        return text


class SignedAgreement(models.Model):
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name="agreements")
    template = models.ForeignKey(AgreementTemplate, on_delete=models.PROTECT, related_name="signatures")
    template_version = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=150)
    rendered_body = models.TextField(help_text="Exact text the driver saw and signed.")
    typed_name = models.CharField(max_length=120)
    signature_image = models.ImageField(upload_to=signature_upload_path, storage=private_storage)
    pdf = models.FileField(upload_to=agreement_pdf_path, storage=private_storage, blank=True)
    content_hash = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    signed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-signed_at"]

    def __str__(self):
        return f"{self.title} — {self.driver} ({self.signed_at:%Y-%m-%d})"

    @staticmethod
    def hash_for(body: str, typed_name: str, signed_at) -> str:
        return hashlib.sha256(f"{body}\n{typed_name}\n{signed_at.isoformat()}".encode()).hexdigest()

    @property
    def reference(self):
        return f"OSP-{self.pk:06d}-{self.content_hash[:8].upper()}"


class ActivityLog(models.Model):
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name="activity")
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=80)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} — {self.driver}"
