from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from complaints.forms import ComplaintAssignForm, ComplaintStatusForm
from complaints.models import Complaint, ComplaintHistory, Notification
from dashboard.forms import EscalationSettingForm
from dashboard.models import SystemSetting
from departments.forms import DepartmentCreateForm, DepartmentUpdateForm
from departments.models import Department


def _is_admin(user):
    return user.is_superuser or getattr(user, "role", "") == "admin"


def _is_department(user):
    return getattr(user, "role", "") == "department"


def _create_notification(user, message):
    Notification.objects.create(user=user, message=message)


@login_required
@user_passes_test(_is_admin)
def admin_dashboard(request):
    setting = SystemSetting.get_solo()
    if request.method == "POST" and "update_escalation" in request.POST:
        form = EscalationSettingForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            messages.success(request, "Escalation days updated.")
            return redirect("dashboard:admin_dashboard")
    else:
        form = EscalationSettingForm(instance=setting)

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
        "dashboard/admin_dashboard.html",
        {
            "complaints": complaints,
            "total": total,
            "pending": pending,
            "resolved": resolved,
            "escalation_days": escalation_days,
            "escalation_form": form,
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
            return redirect("dashboard:admin_dashboard")
    else:
        form = ComplaintAssignForm(instance=complaint)
    return render(request, "dashboard/assign.html", {"form": form, "complaint": complaint})


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
            return redirect("dashboard:admin_dashboard")
    else:
        form = ComplaintAssignForm(instance=complaint)
    return render(request, "dashboard/update.html", {"form": form, "complaint": complaint})


@login_required
@user_passes_test(_is_admin)
def analytics(request):
    total = Complaint.objects.count()
    status_counts = list(Complaint.objects.values("status").annotate(count=Count("id")))
    category_counts = list(Complaint.objects.values("category").annotate(count=Count("id")))

    status_labels = dict(Complaint.Status.choices)
    status_max = max([item["count"] for item in status_counts], default=0)
    status_data = [
        {
            "label": status_labels.get(item["status"], item["status"]),
            "count": item["count"],
            "percent": round((item["count"] / total) * 100) if total else 0,
            "bar": round((item["count"] / status_max) * 100) if status_max else 0,
        }
        for item in status_counts
    ]

    category_max = max([item["count"] for item in category_counts], default=0)
    category_data = [
        {
            "label": item["category"] or "Uncategorized",
            "count": item["count"],
            "percent": round((item["count"] / total) * 100) if total else 0,
            "bar": round((item["count"] / category_max) * 100) if category_max else 0,
        }
        for item in category_counts
    ]
    return render(
        request,
        "dashboard/analytics.html",
        {
            "total": total,
            "status_data": status_data,
            "category_data": category_data,
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
        return redirect("dashboard:admin_dashboard")

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
        line = f"{complaint.unique_id} | {complaint.title} | {complaint.status} | {complaint.priority}"
        pdf.drawString(40, y, line)
        y -= 15
        if y < 60:
            pdf.showPage()
            y = height - 40
    pdf.showPage()
    pdf.save()
    return response


@login_required
@user_passes_test(_is_department)
def department_dashboard(request):
    for complaint in Complaint.objects.filter(unique_id__isnull=True, department__head=request.user):
        complaint.save()
    status_filter = request.GET.get("status")
    category_filter = request.GET.get("category")
    date_filter = request.GET.get("date")

    complaints = Complaint.objects.filter(department__head=request.user).order_by("-created_at")
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    if category_filter:
        complaints = complaints.filter(category__icontains=category_filter)
    if date_filter:
        complaints = complaints.filter(created_at__date=date_filter)

    total = Complaint.objects.filter(department__head=request.user).count()
    pending = Complaint.objects.filter(
        department__head=request.user, status=Complaint.Status.PENDING
    ).count()
    resolved = Complaint.objects.filter(
        department__head=request.user, status=Complaint.Status.RESOLVED
    ).count()

    return render(
        request,
        "dashboard/department_dashboard.html",
        {"complaints": complaints, "total": total, "pending": pending, "resolved": resolved},
    )


@login_required
@user_passes_test(_is_department)
def update_status(request, uid):
    complaint = get_object_or_404(Complaint, unique_id=uid)
    if complaint.department is None or complaint.department.head != request.user:
        messages.error(request, "You are not assigned to this complaint.")
        return redirect("dashboard:department_dashboard")
    if request.method == "POST":
        form = ComplaintStatusForm(request.POST, request.FILES, instance=complaint)
        if form.is_valid():
            complaint = form.save()
            ComplaintHistory.objects.create(
                complaint=complaint,
                status=complaint.status,
                updated_by=request.user,
                remarks=complaint.remarks,
            )
            _create_notification(
                complaint.citizen,
                f"Complaint '{complaint.title}' status updated to {complaint.get_status_display()}.",
            )
            messages.success(request, "Status updated.")
            return redirect("dashboard:department_dashboard")
    else:
        form = ComplaintStatusForm(instance=complaint)
    return render(
        request,
        "dashboard/update_status.html",
        {"form": form, "complaint": complaint},
    )


@login_required
@user_passes_test(_is_admin)
def create_department(request):
    if request.method == "POST":
        form = DepartmentCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department created.")
            return redirect("dashboard:admin_dashboard")
    else:
        form = DepartmentCreateForm()
    return render(request, "dashboard/department_create.html", {"form": form})


@login_required
@user_passes_test(_is_admin)
def list_departments(request):
    departments = Department.objects.select_related("head").order_by("name")
    return render(request, "dashboard/department_list.html", {"departments": departments})


@login_required
@user_passes_test(_is_admin)
def edit_department(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    if request.method == "POST":
        form = DepartmentUpdateForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated.")
            return redirect("dashboard:list_departments")
    else:
        form = DepartmentUpdateForm(instance=department)
    return render(
        request,
        "dashboard/department_edit.html",
        {"form": form, "department": department},
    )


@login_required
@user_passes_test(_is_admin)
def delete_department(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    if request.method == "POST":
        department.delete()
        messages.success(request, "Department deleted.")
        return redirect("dashboard:list_departments")
    return render(
        request,
        "dashboard/department_delete.html",
        {"department": department},
    )
