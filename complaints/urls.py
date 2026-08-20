from django.urls import path

from . import views

app_name = "complaints"

urlpatterns = [
    path("dashboard/", views.citizen_dashboard, name="citizen_dashboard"),
    path("create/", views.create_complaint, name="create"),
    path("confirm/<str:uid>/", views.complaint_confirm, name="confirm"),
    path("<str:uid>/", views.complaint_detail, name="detail"),
    path("<str:uid>/pdf/", views.complaint_pdf, name="complaint_pdf"),
]
