from django.contrib import admin

from .models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "email", "phone", "city", "status", "created_at")
    list_filter = ("kind", "status", "created_at")
    search_fields = ("name", "email", "phone", "message")
    readonly_fields = ("kind", "name", "email", "phone", "city", "message", "extra", "created_at")
    fields = ("kind", "name", "email", "phone", "city", "message", "extra", "created_at", "status", "internal_notes")
    list_editable = ("status",)
    date_hierarchy = "created_at"
