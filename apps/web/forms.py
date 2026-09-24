from django import forms

VEHICLE_YEARS = [("", "Vehicle year")] + [(str(y), str(y)) for y in range(2026, 1999, -1)]


class HoneypotMixin(forms.Form):
    """Bots fill every field; humans never see this one."""

    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""


class DriverApplyForm(HoneypotMixin):
    name = forms.CharField(max_length=120, label="Full name")
    email = forms.EmailField()
    phone = forms.CharField(max_length=40)
    city = forms.CharField(max_length=80, label="City / area", required=False)
    vehicle = forms.CharField(max_length=120, label="Vehicle (make & model)", required=False)
    vehicle_year = forms.ChoiceField(choices=VEHICLE_YEARS, required=False)
    over_21 = forms.BooleanField(label="I am 21 or older with a valid U.S. driver's license", required=True)
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="Anything you want us to know")


class RideRequestForm(HoneypotMixin):
    name = forms.CharField(max_length=120, label="Parent / guardian or school contact")
    email = forms.EmailField()
    phone = forms.CharField(max_length=40)
    organisation = forms.CharField(max_length=120, required=False, label="School or organisation (optional)")
    students = forms.IntegerField(min_value=1, max_value=200, initial=1, label="Number of students")
    pickup_area = forms.CharField(max_length=120, label="Pick-up area / ZIP")
    school = forms.CharField(max_length=120, label="School / destination")
    schedule = forms.CharField(max_length=200, label="Days & times needed", required=False)
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="Details")


class ContactForm(HoneypotMixin):
    name = forms.CharField(max_length=120)
    email = forms.EmailField()
    phone = forms.CharField(max_length=40, required=False)
    topic = forms.ChoiceField(
        choices=[("driver", "Becoming a driver"), ("ride", "Rides for my child / school"), ("partner", "Partnership"), ("other", "Something else")]
    )
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
