from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("complaints/admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("complaints/admin/assign/<str:uid>/", views.assign_complaint, name="assign"),
    path("complaints/admin/update/<str:uid>/", views.update_complaint, name="update"),
    path("complaints/admin/analytics/", views.analytics, name="analytics"),
    path("complaints/admin/report/", views.report_pdf, name="report"),
    path("departments/dashboard/", views.department_dashboard, name="department_dashboard"),
    path("departments/complaints/<str:uid>/status/", views.update_status, name="update_status"),
    path("departments/admin/create/", views.create_department, name="create_department"),
    path("departments/admin/list/", views.list_departments, name="list_departments"),
    path("departments/admin/edit/<int:dept_id>/", views.edit_department, name="edit_department"),
    path("departments/admin/delete/<int:dept_id>/", views.delete_department, name="delete_department"),
]
