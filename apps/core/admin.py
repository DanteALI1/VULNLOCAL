from django.contrib import admin
from .models import SetupProgress, SystemSettings

admin.site.register(SystemSettings)
admin.site.register(SetupProgress)
