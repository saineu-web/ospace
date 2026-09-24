import os

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import WEEKDAYS, DriverDocument, DriverProfile

DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    email = forms.EmailField()
    phone = forms.CharField(max_length=40)
    agree = forms.BooleanField(label="I agree to the privacy policy and to be contacted about my application.")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists. Try signing in instead.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            DriverProfile.objects.create(user=user, phone=self.cleaned_data["phone"])
        return user


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)

    class Meta:
        model = DriverProfile
        fields = [
            "phone", "date_of_birth", "address1", "address2", "city", "state", "zip_code",
            "license_number", "license_state", "license_expiry",
            "vehicle_year", "vehicle_make", "vehicle_model", "vehicle_color", "vehicle_plate", "vehicle_seats",
            "insurance_provider", "insurance_policy", "insurance_expiry",
            "emergency_name", "emergency_phone", "emergency_relationship",
            "how_heard",
        ]
        widgets = {"date_of_birth": DATE, "license_expiry": DATE, "insurance_expiry": DATE}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.instance.user.first_name
        self.fields["last_name"].initial = self.instance.user.last_name
        self.fields["vehicle_year"].widget.attrs.update({"min": 1990, "max": 2027, "placeholder": "2018"})
        self.fields["vehicle_seats"].widget.attrs.update({"min": 1, "max": 12, "placeholder": "4"})
        # Fields the application needs before submission. Left optional at the form level so a
        # driver can save a half-finished profile; the template hides the "(optional)" marker.
        for name in DriverProfile.PROFILE_REQUIRED:
            if name in self.fields:
                self.fields[name].widget.attrs["data_needed"] = "1"
        # availability checkboxes are rendered by hand in the template; read them in clean()
        self.availability = dict(self.instance.availability or {})

    def clean_vehicle_year(self):
        y = self.cleaned_data.get("vehicle_year")
        if y and y < 1990:
            raise forms.ValidationError("Vehicles must be from the last 15 years.")
        return y

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user.first_name = self.cleaned_data["first_name"].strip()
        profile.user.last_name = self.cleaned_data["last_name"].strip()
        profile.availability = self.availability
        if commit:
            profile.user.save(update_fields=["first_name", "last_name"])
            profile.save()
        return profile

    def read_availability(self, post):
        self.availability = {d: [s for s in ("am", "pm") if post.get(f"avail_{d}_{s}")] for d in WEEKDAYS}


class DocumentUploadForm(forms.Form):
    file = forms.FileField()
    expires_on = forms.DateField(required=False, widget=DATE)

    def clean_file(self):
        f = self.cleaned_data["file"]
        ext = os.path.splitext(f.name)[1].lower().lstrip(".")
        if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
            raise forms.ValidationError(f"Please upload a {', '.join(settings.ALLOWED_UPLOAD_EXTENSIONS).upper()} file.")
        if f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError(f"Files must be under {settings.MAX_UPLOAD_MB} MB.")
        return f


class SignForm(forms.Form):
    typed_name = forms.CharField(max_length=120, label="Type your full legal name")
    signature = forms.CharField(widget=forms.HiddenInput)  # data:image/png;base64,...
    consent = forms.BooleanField(label="I have read this document and agree that my electronic signature is legally binding.")

    def clean_signature(self):
        sig = self.cleaned_data["signature"]
        if not sig.startswith("data:image/png;base64,") or len(sig) < 200:
            raise forms.ValidationError("Please draw your signature in the box.")
        if len(sig) > 400_000:
            raise forms.ValidationError("Signature is too large. Please try again.")
        return sig


class ReviewDocumentForm(forms.Form):
    status = forms.ChoiceField(choices=DriverDocument.STATUS_CHOICES)
    review_note = forms.CharField(max_length=300, required=False)


class ReviewDriverForm(forms.Form):
    status = forms.ChoiceField(choices=DriverProfile.STATUS_CHOICES)
    review_message = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="Message to driver")
    internal_notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
