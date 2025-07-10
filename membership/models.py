from datetime import timedelta
from django.utils import timezone
from django.db import models


class PasswordResetToken(models.Model):
    email = models.EmailField()
    token = models.CharField(max_length=100, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(hours=1)
