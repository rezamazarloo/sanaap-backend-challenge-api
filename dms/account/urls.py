from account.views import (
    AssignUserGroupView,
    GroupListView,
    LoginView,
    LogoutView,
    SignupView,
    UserDetailView,
    UserListCreateView,
)
from django.urls import path

app_name = "account"

urlpatterns = [
    path("auth/signup/", SignupView.as_view(), name="signup"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("users/", UserListCreateView.as_view(), name="user-list"),
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path(
        "users/<int:user_id>/assign-group/",
        AssignUserGroupView.as_view(),
        name="user-assign-group",
    ),
    path("groups/", GroupListView.as_view(), name="group-list"),
]
