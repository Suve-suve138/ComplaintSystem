from django.urls import path

from . import views

app_name = "departments"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("complaints/<str:uid>/status/", views.update_status, name="update_status"),
    path("admin/create/", views.create_department, name="create"),
    path("admin/list/", views.list_departments, name="list"),
]
