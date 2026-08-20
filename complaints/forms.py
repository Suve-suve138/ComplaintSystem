from django import forms

from .models import Comment, Complaint, Feedback


class ComplaintCreateForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["title", "description", "category", "priority", "image", "location"]


class ComplaintAssignForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["department", "priority", "status"]


class ComplaintStatusForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["status", "remarks", "proof"]


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["rating", "comment"]


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["message"]
