from account.permissions import (
    CanAssignUserGroup,
    CanCreateUser,
    CanViewGroup,
    CanViewUser,
)
from account.schema import (
    GROUP_LIST_SCHEMA,
    LOGIN_POST_SCHEMA,
    LOGOUT_POST_SCHEMA,
    SIGNUP_POST_SCHEMA,
    USER_DETAIL_SCHEMA,
    USER_GROUP_ASSIGN_POST_SCHEMA,
    USER_LIST_CREATE_SCHEMA,
)
from account.serializers import (
    AssignUserGroupSerializer,
    GroupListSerializer,
    SignupResponseSerializer,
    SignupSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
)
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class SignupView(APIView):
    permission_classes = [AllowAny]

    @SIGNUP_POST_SCHEMA
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            SignupResponseSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class LoginView(ObtainAuthToken):
    permission_classes = [AllowAny]

    @LOGIN_POST_SCHEMA
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @LOGOUT_POST_SCHEMA
    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@USER_LIST_CREATE_SCHEMA
class UserListCreateView(ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), CanCreateUser()]
        return [IsAuthenticated(), CanViewUser()]

    def get_queryset(self):
        return get_user_model().objects.order_by("-date_joined")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserListSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserDetailSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


@USER_DETAIL_SCHEMA
class UserDetailView(RetrieveAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated, CanViewUser]
    lookup_url_kwarg = "user_id"

    def get_queryset(self):
        return get_user_model().objects.prefetch_related("groups").order_by("id")


@GROUP_LIST_SCHEMA
class GroupListView(ListAPIView):
    queryset = Group.objects.order_by("name")
    serializer_class = GroupListSerializer
    permission_classes = [IsAuthenticated, CanViewGroup]


class UserGroupAssignView(APIView):
    permission_classes = [IsAuthenticated, CanAssignUserGroup]

    @USER_GROUP_ASSIGN_POST_SCHEMA
    def post(self, request, user_id):
        user = get_object_or_404(
            get_user_model().objects.prefetch_related("groups"),
            pk=user_id,
        )
        serializer = AssignUserGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.groups.add(serializer.validated_data["group"])
        user = get_user_model().objects.prefetch_related("groups").get(pk=user.pk)

        return Response(UserDetailSerializer(user).data, status=status.HTTP_200_OK)
