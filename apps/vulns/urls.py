from django.urls import path

from . import views

app_name = "vulns"

urlpatterns = [
    path("", views.vuln_list, name="list"),
    path("create/", views.vuln_create_local, name="create"),
    path("<int:pk>/", views.vuln_detail, name="detail"),
]
