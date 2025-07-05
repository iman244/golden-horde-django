from django.contrib import admin
from .models import Horde, Tent

@admin.register(Horde)
class HordeAdmin(admin.ModelAdmin):
    pass

@admin.register(Tent)
class TentAdmin(admin.ModelAdmin):
    pass
