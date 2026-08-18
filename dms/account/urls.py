from account.views import LoginView, LogoutView, SignupView
from django.urls import path

app_name = "account"

urlpatterns = [
    path("auth/signup/", SignupView.as_view(), name="signup"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
]
