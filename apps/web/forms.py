from django import forms
from django.utils.translation import gettext_lazy as _

VEHICLE_YEARS = [("", _("Vehicle year"))] + [(str(y), str(y)) for y in range(2026, 1999, -1)]

VEHICLE_TYPES = [
    ("", _("Vehicle type")),
    ("sedan", _("Sedan (4-door)")),
    ("suv", _("SUV / crossover")),
    ("minivan", _("Minivan")),
    ("hatchback", _("Hatchback (4-door)")),
    ("pickup", _("Pickup truck (4-door)")),
    ("van", _("Van (8+ seats)")),
    ("other", _("Other")),
]


class HoneypotMixin(forms.Form):
    """Bots fill every field; humans never see this one."""

    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""


class DriverApplyForm(HoneypotMixin):
    first_name = forms.CharField(max_length=60, label=_("First name"))
    last_name = forms.CharField(max_length=60, label=_("Last name"))
    email = forms.EmailField(label=_("Email"))
    phone = forms.CharField(max_length=40, label=_("Phone"))
    city = forms.CharField(max_length=80, label=_("City / area"))
    vehicle_type = forms.ChoiceField(choices=VEHICLE_TYPES, label=_("Vehicle type"))
    vehicle_year = forms.ChoiceField(choices=VEHICLE_YEARS, label=_("Vehicle year"))
    over_21 = forms.BooleanField(label=_("I am 21 or older with a valid U.S. driver's license"), required=True)
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label=_("Anything you want us to know"))

    @property
    def full_name(self):
        d = self.cleaned_data
        return f"{d['first_name'].strip()} {d['last_name'].strip()}".strip()


class RideRequestForm(HoneypotMixin):
    name = forms.CharField(max_length=120, label=_("Parent / guardian or school contact"))
    email = forms.EmailField(label=_("Email"))
    phone = forms.CharField(max_length=40, label=_("Phone"))
    organisation = forms.CharField(max_length=120, required=False, label=_("School or organisation"))
    students = forms.IntegerField(min_value=1, max_value=200, initial=1, label=_("Number of students"))
    pickup_area = forms.CharField(max_length=120, label=_("Pick-up area / ZIP"))
    school = forms.CharField(max_length=120, label=_("School / destination"))
    schedule = forms.CharField(max_length=200, label=_("Days & times needed"), required=False)
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label=_("Details"))


class ContactForm(HoneypotMixin):
    name = forms.CharField(max_length=120, label=_("Name"))
    email = forms.EmailField(label=_("Email"))
    phone = forms.CharField(max_length=40, required=False, label=_("Phone"))
    topic = forms.ChoiceField(
        label=_("Topic"),
        choices=[
            ("driver", _("Becoming a driver")),
            ("ride", _("Rides for my child / school")),
            ("partner", _("Partnership")),
            ("other", _("Something else")),
        ],
    )
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), label=_("Message"))
