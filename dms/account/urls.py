from account.views import (
    GroupListView,
    LoginView,
    LogoutView,
    SignupView,
    UserDetailView,
    UserGroupAssignView,
    UserListCreateView,
)
from django.urls import path

app_name = "account"

urlpatterns = [
    path("auth/signup/", SignupView.as_view(), name="signup"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("users/", UserListCreateView.as_view(), name="user-list-create"),
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path(
        "users/<int:user_id>/assign-group/",
        UserGroupAssignView.as_view(),
        name="user-group-assign",
    ),
    path("groups/", GroupListView.as_view(), name="group-list"),
]
