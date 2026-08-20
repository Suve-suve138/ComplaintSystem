from django.db import models


class SystemSetting(models.Model):
    escalation_days = models.PositiveIntegerField(default=5)

    def __str__(self) -> str:
        return f"SystemSetting(escalation_days={self.escalation_days})"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def get_escalation_days(cls, fallback: int = 5) -> int:
        try:
            return cls.get_solo().escalation_days
        except Exception:
            return fallback
