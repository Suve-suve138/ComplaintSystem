from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        CITIZEN = "citizen", "Citizen"
        ADMIN = "admin", "Admin"
        DEPARTMENT = "department", "Department"

    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.CITIZEN)

    def is_admin(self):
        return self.role == self.Roles.ADMIN

    def is_department(self):
        return self.role == self.Roles.DEPARTMENT
