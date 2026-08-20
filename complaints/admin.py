from django.contrib import admin

from .models import Comment, Complaint, ComplaintHistory, Feedback, Notification


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ["title", "citizen", "status", "priority", "department", "created_at"]
    list_filter = ["status", "priority", "category"]
    search_fields = ["title", "description", "category"]


admin.site.register(ComplaintHistory)
admin.site.register(Notification)
admin.site.register(Feedback)
admin.site.register(Comment)
