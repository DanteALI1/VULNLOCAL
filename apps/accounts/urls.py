from django.urls import path
from .views import NovaLoginView, NovaLogoutView

app_name = "accounts"
urlpatterns = [
    path("login/", NovaLoginView.as_view(), name="login"),
    path("logout/", NovaLogoutView.as_view(), name="logout"),
]
