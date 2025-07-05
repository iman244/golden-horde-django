from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User


class Horde(models.Model):
    name = models.CharField(_("name"), max_length=255)
    greatkhan = models.ForeignKey(User, verbose_name=_("greatkhan"), on_delete=models.CASCADE, related_name="hordes")

    def __str__(self):
        return self.name

class Tent(models.Model):
    name = models.CharField(_("name"), max_length=255)
    horde = models.ForeignKey(Horde, verbose_name=_("horde"), on_delete=models.CASCADE, related_name="tents")
    
    def __str__(self):
        return self.name
