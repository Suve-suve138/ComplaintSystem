from django import forms

from .models import SystemSetting


class EscalationSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = ["escalation_days"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["escalation_days"].widget.attrs.update(
            {"class": "form-control", "min": "1"}
        )

    def clean_escalation_days(self):
        value = self.cleaned_data["escalation_days"]
        if value < 1:
            raise forms.ValidationError("Escalation days must be at least 1.")
        return value
