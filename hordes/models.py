from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Horde(models.Model):
    name = models.CharField(_("name"), max_length=255)
    greatkhan = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("greatkhan"), on_delete=models.CASCADE, related_name="hordes")

    def __str__(self):
        return self.name


class Tent(models.Model):
    name = models.CharField(_("name"), max_length=255)
    horde = models.ForeignKey(Horde, verbose_name=_("horde"), on_delete=models.CASCADE, related_name="tents")
    
    def __str__(self):
        return self.name


class TentParticipant(models.Model):
    tent = models.ForeignKey(Tent, on_delete=models.CASCADE, related_name="participants")
    username = models.CharField(max_length=150)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tent", "username")

    def __str__(self):
        return f"{self.username} in {self.tent.name}"

