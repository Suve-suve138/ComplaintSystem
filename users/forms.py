from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = User.Roles.CITIZEN
        if commit:
            user.save()
        return user
