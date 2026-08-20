from django.conf import settings
from django.db import models
from django.utils import timezone
import secrets
import string


class Complaint(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    unique_id = models.CharField(max_length=12, editable=False, unique=True, null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    image = models.ImageField(upload_to="complaints/images/", blank=True, null=True)
    location = models.CharField(max_length=200, blank=True)

    citizen = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaints"
    )
    department = models.ForeignKey(
        "departments.Department", on_delete=models.SET_NULL, null=True, blank=True
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
    )

    remarks = models.TextField(blank=True)
    proof = models.FileField(upload_to="complaints/proof/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    escalated = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(blank=True, null=True)

    def mark_escalated(self):
        if not self.escalated:
            self.escalated = True
            self.escalated_at = timezone.now()
            self.priority = self.Priority.HIGH
            self.save(update_fields=["escalated", "escalated_at", "priority"])

    def save(self, *args, **kwargs):
        if not self.unique_id:
            alphabet = string.ascii_uppercase + string.digits
            # Example: CMPA7X9Q
            self.unique_id = "CMP" + "".join(secrets.choice(alphabet) for _ in range(6))
            while Complaint.objects.filter(unique_id=self.unique_id).exists():
                self.unique_id = "CMP" + "".join(secrets.choice(alphabet) for _ in range(6))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class ComplaintHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="history")
    status = models.CharField(max_length=20, choices=Complaint.Status.choices)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Feedback(models.Model):
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name="feedback")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Comment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
