from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render

from .forms import RegisterForm
from .models import User


def home(request):
    return render(request, "users/home.html")


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created. Please log in.")
            return redirect("users:login")
    else:
        form = RegisterForm()
    return render(request, "users/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("users:dashboard")
    else:
        form = AuthenticationForm()
    return render(request, "users/login.html", {"form": form})


def org_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_superuser and user.role not in (User.Roles.ADMIN, User.Roles.DEPARTMENT):
                messages.error(request, "This login is only for Admin/Department users.")
                return redirect("users:org_login")
            login(request, user)
            return redirect("users:dashboard")
    else:
        form = AuthenticationForm()
    return render(request, "users/org_login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("users:login")


@login_required
def dashboard(request):
    user = request.user
    if user.is_superuser or user.role == User.Roles.ADMIN:
        return redirect("dashboard:admin_dashboard")
    if user.role == User.Roles.DEPARTMENT:
        return redirect("dashboard:department_dashboard")
    return redirect("complaints:citizen_dashboard")
