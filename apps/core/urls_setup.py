from django.urls import path

from .views_setup import SetupWizardView

urlpatterns = [
    path("", SetupWizardView.as_view(), name="setup"),
]
