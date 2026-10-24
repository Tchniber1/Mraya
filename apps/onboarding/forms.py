import json

from django import forms
from django.conf import settings

from apps.analysis.countries import COUNTRIES, DEFAULT_CURRENCY
from apps.analysis.images import InvalidImage, load_image
from apps.analysis.prompts import CATEGORIES

CURRENCIES = [
    ("MAD", "MAD (DH)"), ("EUR", "EUR (€)"), ("USD", "USD ($)"), ("GBP", "GBP (£)"),
    ("CAD", "CAD (CA$)"), ("AED", "AED"), ("SAR", "SAR"),
]
COUNTRY_CHOICES = sorted(COUNTRIES.items(), key=lambda item: item[1])
PROFILE_FIELDS = (
    "gender", "age", "budget", "currency", "country", "city",
    "style_preferences", "brand_preferences", "suggest_brands", "interests",
)


class OnboardingForm(forms.Form):
    gender = forms.ChoiceField(choices=[("men", "Man"), ("women", "Woman")], widget=forms.RadioSelect)
    age = forms.IntegerField(min_value=13, max_value=100)
    budget = forms.IntegerField(min_value=50, max_value=1_000_000)
    currency = forms.ChoiceField(choices=CURRENCIES, initial="MAD")
    country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        initial=settings.SERPER_COUNTRY,
        widget=forms.Select(attrs={"data-currency-for": json.dumps(DEFAULT_CURRENCY)}),
    )
    city = forms.CharField(max_length=80, required=False)
    style_preferences = forms.CharField(
        max_length=400, required=False, widget=forms.Textarea(attrs={"rows": 2})
    )
    brand_preferences = forms.CharField(max_length=200, required=False)
    suggest_brands = forms.BooleanField(required=False, initial=True)
    interests = forms.MultipleChoiceField(
        choices=list(CATEGORIES.items()),
        widget=forms.CheckboxSelectMultiple,
        initial=list(CATEGORIES),
    )
    full_body = forms.FileField()
    face = forms.FileField()

    def _clean_image(self, field):
        upload = self.cleaned_data[field]
        try:
            return load_image(upload.read(), settings.MRAYA_MAX_IMAGE_BYTES)
        except InvalidImage as exc:
            raise forms.ValidationError(str(exc)) from None

    def clean_full_body(self):
        return self._clean_image("full_body")

    def clean_face(self):
        return self._clean_image("face")

    def profile(self):
        return {name: self.cleaned_data[name] for name in PROFILE_FIELDS}


def initial_from_user(user):
    initial = {name: user[name] for name in PROFILE_FIELDS if user.get(name) not in (None, "")}
    initial.setdefault("currency", "MAD")
    initial.setdefault("country", settings.SERPER_COUNTRY)
    initial.setdefault("suggest_brands", True)
    initial.setdefault("interests", list(CATEGORIES))
    return initial
