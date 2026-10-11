"""Profiles created under the old flow (self-registered, status 'draft') already have a password
and were working on documents, so they map onto the new 'in_progress' status."""
from django.db import migrations


def forwards(apps, schema_editor):
    DriverProfile = apps.get_model("portal", "DriverProfile")
    DriverProfile.objects.filter(status="draft").update(status="in_progress")


def backwards(apps, schema_editor):
    DriverProfile = apps.get_model("portal", "DriverProfile")
    DriverProfile.objects.filter(status="in_progress").update(status="draft")


class Migration(migrations.Migration):
    dependencies = [("portal", "0003_interested_flow")]
    operations = [migrations.RunPython(forwards, backwards)]
