from django import forms
from django.contrib.auth.forms import UserCreationForm

from users.models import User

from .models import Department


class DepartmentCreateForm(UserCreationForm):
    department_name = forms.CharField(max_length=100, label="Department Name")
    description = forms.CharField(widget=forms.Textarea, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = User.Roles.DEPARTMENT
        if commit:
            user.save()
        Department.objects.create(
            name=self.cleaned_data["department_name"],
            description=self.cleaned_data.get("description", ""),
            head=user,
        )
        return user


class DepartmentUpdateForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "description", "head"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["head"].queryset = User.objects.filter(role=User.Roles.DEPARTMENT)
        self.fields["head"].required = False
