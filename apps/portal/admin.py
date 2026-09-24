from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import ActivityLog, AgreementTemplate, DocumentType, DriverDocument, DriverProfile, SignedAgreement


class DocumentInline(admin.TabularInline):
    model = DriverDocument
    extra = 0
    fields = ("doc_type", "original_name", "status", "review_note", "expires_on", "uploaded_at")
    readonly_fields = ("doc_type", "original_name", "uploaded_at")
    can_delete = False


class AgreementInline(admin.TabularInline):
    model = SignedAgreement
    extra = 0
    fields = ("title", "template_version", "typed_name", "signed_at", "pdf_link")
    readonly_fields = fields
    can_delete = False

    def pdf_link(self, obj):
        return format_html('<a href="{}" target="_blank">PDF</a>', reverse("portal:agreement_pdf", args=[obj.pk])) if obj.pk else ""


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "status", "city", "vehicle", "created_at", "review_link")
    list_filter = ("status", "state", "created_at")
    search_fields = ("user__first_name", "user__last_name", "user__email", "phone", "vehicle_plate")
    readonly_fields = ("user", "created_at", "updated_at", "submitted_at", "reviewed_at", "reviewed_by")
    inlines = [DocumentInline, AgreementInline]
    fieldsets = (
        ("Account", {"fields": ("user", "status", "review_message", "internal_notes")}),
        ("Personal", {"fields": ("phone", "date_of_birth", ("address1", "address2"), ("city", "state", "zip_code"))}),
        ("License", {"fields": (("license_number", "license_state", "license_expiry"),)}),
        ("Vehicle", {"fields": (("vehicle_year", "vehicle_make", "vehicle_model"), ("vehicle_color", "vehicle_plate", "vehicle_seats"))}),
        ("Insurance", {"fields": (("insurance_provider", "insurance_policy", "insurance_expiry"),)}),
        ("Emergency contact", {"fields": (("emergency_name", "emergency_phone", "emergency_relationship"),)}),
        ("Other", {"fields": ("availability", "how_heard", "submitted_at", "reviewed_at", "reviewed_by", "created_at", "updated_at")}),
    )

    @admin.display(description="Vehicle")
    def vehicle(self, obj):
        return " ".join(str(x) for x in (obj.vehicle_year, obj.vehicle_make, obj.vehicle_model) if x)

    @admin.display(description="Review")
    def review_link(self, obj):
        return format_html('<a href="{}">Open review desk</a>', reverse("staff:driver", args=[obj.pk]))


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "required", "has_expiry", "sort_order", "active")
    list_editable = ("required", "has_expiry", "sort_order", "active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(AgreementTemplate)
class AgreementTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "version", "required", "sort_order", "active", "updated_at")
    list_editable = ("required", "sort_order", "active")
    prepopulated_fields = {"slug": ("title",)}
    fields = ("title", "slug", "summary", "body", "version", "required", "sort_order", "active")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["body"].help_text = (
            "Plain text. Blank line between paragraphs; start a line with '# ' for a section heading. "
            "Placeholders: {{driver_name}} {{driver_email}} {{driver_phone}} {{date}} {{company}} {{vehicle}}. "
            "After changing the wording, increase the version so drivers sign the new text."
        )
        form.base_fields["body"].widget.attrs.update({"rows": 28, "style": "width:100%;font-family:monospace"})
        return form


@admin.register(DriverDocument)
class DriverDocumentAdmin(admin.ModelAdmin):
    list_display = ("doc_type", "driver", "status", "expires_on", "uploaded_at", "file_link")
    list_filter = ("status", "doc_type")
    search_fields = ("driver__user__first_name", "driver__user__last_name", "driver__user__email")
    readonly_fields = ("driver", "doc_type", "file", "original_name", "size", "content_type", "uploaded_at", "file_link")

    def file_link(self, obj):
        return format_html('<a href="{}" target="_blank">Open</a>', reverse("portal:document_file", args=[obj.pk])) if obj.pk else ""


@admin.register(SignedAgreement)
class SignedAgreementAdmin(admin.ModelAdmin):
    list_display = ("title", "driver", "template_version", "typed_name", "signed_at", "pdf_link")
    list_filter = ("template",)
    search_fields = ("driver__user__first_name", "driver__user__last_name", "driver__user__email", "typed_name")
    readonly_fields = [f.name for f in SignedAgreement._meta.fields] + ["pdf_link"]

    def pdf_link(self, obj):
        return format_html('<a href="{}" target="_blank">PDF</a>', reverse("portal:agreement_pdf", args=[obj.pk])) if obj.pk else ""

    def has_add_permission(self, request):
        return False


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "driver", "action", "detail", "actor")
    list_filter = ("action",)
    readonly_fields = [f.name for f in ActivityLog._meta.fields]
