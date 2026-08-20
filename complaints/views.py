from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CommentForm, ComplaintAssignForm, ComplaintCreateForm, ComplaintStatusForm, FeedbackForm
from .models import Comment, Complaint, ComplaintHistory, Feedback, Notification
from dashboard.models import SystemSetting


def _is_admin(user):
    return user.is_superuser or getattr(user, "role", "") == "admin"


def _is_department(user):
    return getattr(user, "role", "") == "department"


def _create_notification(user, message):
    Notification.objects.create(user=user, message=message)


@login_required
def citizen_dashboard(request):
    for complaint in Complaint.objects.filter(unique_id__isnull=True, citizen=request.user):
        complaint.save()
    complaints = Complaint.objects.filter(citizen=request.user).order_by("-created_at")
    return render(request, "complaints/citizen_dashboard.html", {"complaints": complaints})


@login_required
def create_complaint(request):
    if request.method == "POST":
        form = ComplaintCreateForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.citizen = request.user
            complaint.save()
            ComplaintHistory.objects.create(
                complaint=complaint, status=complaint.status, updated_by=request.user
            )
            _create_notification(
                request.user, f"Complaint '{complaint.title}' submitted successfully."
            )
            messages.success(request, "Complaint submitted.")
            return redirect("complaints:confirm", uid=complaint.unique_id)
    else:
        form = ComplaintCreateForm()
    return render(request, "complaints/create.html", {"form": form})


@login_required
def complaint_confirm(request, uid):
    complaint = get_object_or_404(Complaint, unique_id=uid, citizen=request.user)
    return render(request, "complaints/confirm.html", {"complaint": complaint})


@login_required
def complaint_detail(request, uid):
    complaint = get_object_or_404(Complaint, unique_id=uid)
    comments = complaint.comments.select_related("author").order_by("created_at")
    feedback_form = None
    comment_form = CommentForm()

    if complaint.citizen != request.user and not _is_admin(request.user) and not _is_department(
        request.user
    ):
        return redirect("users:dashboard")
    if _is_department(request.user):
        if complaint.department is None or complaint.department.head != request.user:
            return redirect("users:dashboard")

    if request.method == "POST":
        if "add_comment" in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.complaint = complaint
                comment.author = request.user
                comment.save()
                messages.success(request, "Comment added.")
                return redirect("complaints:detail", uid=uid)
        elif "add_feedback" in request.POST and complaint.status == Complaint.Status.RESOLVED:
            feedback_form = FeedbackForm(request.POST)
            if feedback_form.is_valid():
                feedback = feedback_form.save(commit=False)
                feedback.complaint = complaint
                feedback.save()
                messages.success(request, "Feedback submitted.")
                return redirect("complaints:detail", uid=uid)
    if complaint.status == Complaint.Status.RESOLVED and not hasattr(complaint, "feedback"):
        feedback_form = feedback_form or FeedbackForm()

    if _is_admin(request.user):
        template = "dashboard/detail_admin.html"
    elif _is_department(request.user):
        template = "dashboard/detail_department.html"
    else:
        template = "complaints/detail.html"

    return render(
        request,
        template,
        {
            "complaint": complaint,
            "comments": comments,
            "comment_form": comment_form,
            "feedback_form": feedback_form,
        },
    )


@login_required
@user_passes_test(_is_admin)
def admin_dashboard(request):
    for complaint in Complaint.objects.filter(unique_id__isnull=True):
        complaint.save()
    escalation_days = SystemSetting.get_escalation_days(
        fallback=getattr(settings, "ESCALATION_DAYS", 5)
    )
    threshold = timezone.now() - timedelta(days=escalation_days)
    overdue = Complaint.objects.filter(status__in=["pending", "in_progress"], created_at__lt=threshold)
    for complaint in overdue:
        complaint.mark_escalated()

    status_filter = request.GET.get("status")
    category_filter = request.GET.get("category")
    date_filter = request.GET.get("date")

    complaints = Complaint.objects.all().order_by("-created_at")
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    if category_filter:
        complaints = complaints.filter(category__icontains=category_filter)
    if date_filter:
        complaints = complaints.filter(created_at__date=date_filter)

    total = Complaint.objects.count()
    pending = Complaint.objects.filter(status=Complaint.Status.PENDING).count()
    resolved = Complaint.objects.filter(status=Complaint.Status.RESOLVED).count()

    return render(
        request,
        "complaints/admin_dashboard.html",
        {
            "complaints": complaints,
            "total": total,
            "pending": pending,
            "resolved": resolved,
            "escalation_days": escalation_days,
        },
    )


@login_required
@user_passes_test(_is_admin)
def assign_complaint(request, uid):
    complaint = get_object_or_404(Complaint, unique_id=uid)
    if request.method == "POST":
        form = ComplaintAssignForm(request.POST, instance=complaint)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.assigned_by = request.user
            complaint.save()
            ComplaintHistory.objects.create(
                complaint=complaint,
                status=complaint.status,
                updated_by=request.user,
                remarks="Assigned to department",
            )
            if complaint.department and complaint.department.head:
                _create_notification(
                    complaint.department.head,
                    f"Complaint '{complaint.title}' assigned to your department.",
                )
            messages.success(request, "Complaint assigned.")
            return redirect("complaints:admin_dashboard")
    else:
        form = ComplaintAssignForm(instance=complaint)
    return render(request, "complaints/assign.html", {"form": form, "complaint": complaint})


@login_required
@user_passes_test(_is_admin)
def update_complaint(request, uid):
    complaint = get_object_or_404(Complaint, unique_id=uid)
    if request.method == "POST":
        form = ComplaintAssignForm(request.POST, instance=complaint)
        if form.is_valid():
            complaint = form.save()
            ComplaintHistory.objects.create(
                complaint=complaint, status=complaint.status, updated_by=request.user
            )
            _create_notification(
                complaint.citizen, f"Complaint '{complaint.title}' updated by admin."
            )
            messages.success(request, "Complaint updated.")
            return redirect("complaints:admin_dashboard")
    else:
        form = ComplaintAssignForm(instance=complaint)
    return render(request, "complaints/update.html", {"form": form, "complaint": complaint})


@login_required
@user_passes_test(_is_admin)
def analytics(request):
    total = Complaint.objects.count()
    status_counts = Complaint.objects.values("status").annotate(count=Count("id"))
    category_counts = Complaint.objects.values("category").annotate(count=Count("id"))
    return render(
        request,
        "complaints/analytics.html",
        {
            "total": total,
            "status_counts": status_counts,
            "category_counts": category_counts,
        },
    )


@login_required
@user_passes_test(_is_admin)
def report_pdf(request):
    complaints = Complaint.objects.all().order_by("-created_at")
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        messages.error(request, "ReportLab is required for PDF export. Install reportlab.")
        return redirect("complaints:admin_dashboard")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=complaints_report.pdf"
    pdf = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    y = height - 40
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "Complaint Report")
    y -= 30
    pdf.setFont("Helvetica", 10)
    for complaint in complaints:
        line = f"{complaint.id} | {complaint.title} | {complaint.status} | {complaint.priority}"
        pdf.drawString(40, y, line)
        y -= 15
        if y < 60:
            pdf.showPage()
            y = height - 40
    pdf.showPage()
    pdf.save()
    return response


@login_required
def complaint_pdf(request, uid):
    complaint = get_object_or_404(Complaint, unique_id=uid)
    if complaint.citizen != request.user and not _is_admin(request.user) and not _is_department(
        request.user
    ):
        return redirect("users:dashboard")
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        messages.error(request, "ReportLab is required for PDF export. Install reportlab.")
        return redirect("complaints:detail", uid=uid)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f"attachment; filename=complaint_{complaint.unique_id}.pdf"
    )
    pdf = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    y = height - 40
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "Complaint Confirmation")
    y -= 25
    pdf.setFont("Helvetica", 11)
    lines = [
        f"Complaint ID: {complaint.unique_id}",
        f"Title: {complaint.title}",
        f"Status: {complaint.get_status_display()}",
        f"Priority: {complaint.get_priority_display()}",
        f"Category: {complaint.category}",
        f"Location: {complaint.location or '-'}",
        f"Created At: {complaint.created_at.strftime('%Y-%m-%d %H:%M')}",
    ]
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 16
    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, "Description:")
    y -= 16
    pdf.setFont("Helvetica", 11)
    for chunk in complaint.description.splitlines() or ["-"]:
        pdf.drawString(40, y, chunk[:100])
        y -= 14
        if y < 60:
            pdf.showPage()
            y = height - 40
    pdf.showPage()
    pdf.save()
    return response
