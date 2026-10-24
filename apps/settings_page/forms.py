from django import forms
from django.conf import settings

from apps.analysis.images import InvalidImage, load_image
from apps.onboarding.forms import COUNTRY_CHOICES, CURRENCIES


class SettingsForm(forms.Form):
    display_name = forms.CharField(max_length=60)
    gender = forms.ChoiceField(choices=[("men", "Man"), ("women", "Woman")], label="Theme")
    country = forms.ChoiceField(choices=COUNTRY_CHOICES, label="Shopping country")
    currency = forms.ChoiceField(choices=CURRENCIES)


class AvatarForm(forms.Form):
    avatar = forms.FileField()

    def clean_avatar(self):
        try:
            return load_image(self.cleaned_data["avatar"].read(), settings.MRAYA_MAX_IMAGE_BYTES)
        except InvalidImage as exc:
            raise forms.ValidationError(str(exc)) from None
