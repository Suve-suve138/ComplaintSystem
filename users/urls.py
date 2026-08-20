from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("org/login/", views.org_login, name="org_login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
