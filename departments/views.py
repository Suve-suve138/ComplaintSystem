from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from complaints.forms import ComplaintStatusForm
from complaints.models import Complaint, ComplaintHistory, Notification
from .forms import DepartmentCreateForm
from .models import Department


def _is_department(user):
    return getattr(user, "role", "") == "department"


def _is_admin(user):
    return user.is_superuser or getattr(user, "role", "") == "admin"


def _create_notification(user, message):
    Notification.objects.create(user=user, message=message)


@login_required
@user_passes_test(_is_department)
def dashboard(request):
    for complaint in Complaint.objects.filter(unique_id__isnull=True, department__head=request.user):
        complaint.save()
    complaints = Complaint.objects.filter(department__head=request.user).order_by("-created_at")
    return render(request, "departments/dashboard.html", {"complaints": complaints})


@login_required
@user_passes_test(_is_department)
def update_status(request, uid):
    complaint = get_object_or_404(Complaint, unique_id=uid)
    if complaint.department is None or complaint.department.head != request.user:
        messages.error(request, "You are not assigned to this complaint.")
        return redirect("departments:dashboard")
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
            return redirect("departments:dashboard")
    else:
        form = ComplaintStatusForm(instance=complaint)
    return render(
        request,
        "departments/update_status.html",
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
            return redirect("complaints:admin_dashboard")
    else:
        form = DepartmentCreateForm()
    return render(request, "departments/create.html", {"form": form})


@login_required
@user_passes_test(_is_admin)
def list_departments(request):
    departments = Department.objects.select_related("head").order_by("name")
    return render(request, "departments/list.html", {"departments": departments})
