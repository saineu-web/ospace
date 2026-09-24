from django.db import models


class Inquiry(models.Model):
    """Every public form on the marketing site lands here, and is also emailed."""

    KIND_CHOICES = [
        ("driver", "Driver application"),
        ("ride", "Ride request (family / school)"),
        ("contact", "General contact"),
    ]
    STATUS_CHOICES = [("new", "New"), ("contacted", "Contacted"), ("closed", "Closed")]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    city = models.CharField(max_length=80, blank=True)
    message = models.TextField(blank=True)
    extra = models.JSONField(default=dict, blank=True, help_text="Form-specific fields (vehicle, school, schedule...)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    internal_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Website inquiry"
        verbose_name_plural = "Website inquiries"

    def __str__(self):
        return f"{self.get_kind_display()} — {self.name}"
