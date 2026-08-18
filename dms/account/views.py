from account.permissions import (
    CanAssignUserGroup,
    CanCreateUser,
    CanViewGroup,
    CanViewUser,
)
from account.serializers import (
    AssignUserGroupSerializer,
    GroupListSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    SignupResponseSerializer,
    SignupSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
)
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


AUTH_TAG = "Authentication"
USERS_TAG = "Users"
GROUPS_TAG = "Groups"

UNAUTHORIZED_RESPONSE = OpenApiResponse(
    description="Authentication credentials were not provided or are invalid."
)
FORBIDDEN_RESPONSE = OpenApiResponse(
    description="The authenticated user does not have the required permission."
)
NOT_FOUND_RESPONSE = OpenApiResponse(description="The requested resource was not found.")


class SignupView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        auth=[],
        summary="Create account",
        description="Register a new user account with a username and password.",
        request=SignupSerializer,
        responses={
            status.HTTP_201_CREATED: SignupResponseSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid signup data."
            ),
        },
        tags=[AUTH_TAG],
    )
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

    @extend_schema(
        auth=[],
        summary="Log in",
        description="Exchange a username and password for an authentication token.",
        request=LoginSerializer,
        responses={
            status.HTTP_200_OK: LoginResponseSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid username or password."
            ),
        },
        tags=[AUTH_TAG],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Log out",
        description="Delete the authenticated user's token.",
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="Logged out."),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
        },
        tags=[AUTH_TAG],
    )
    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(
        summary="List users",
        description=(
            "Return users with lightweight fields. Requires `auth.view_user`."
        ),
        responses={
            status.HTTP_200_OK: UserListSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
        },
        tags=[USERS_TAG],
    ),
    post=extend_schema(
        summary="Create user",
        description="Create a new user account. Requires `auth.add_user`.",
        request=UserCreateSerializer,
        responses={
            status.HTTP_201_CREATED: UserDetailSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid user data."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
        },
        tags=[USERS_TAG],
    ),
)
class UserListCreateView(generics.ListCreateAPIView):
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


@extend_schema(
    summary="Get user",
    description="Return a single user with group membership. Requires `auth.view_user`.",
    responses={
        status.HTTP_200_OK: UserDetailSerializer,
        status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
        status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
        status.HTTP_404_NOT_FOUND: NOT_FOUND_RESPONSE,
    },
    tags=[USERS_TAG],
)
class UserDetailView(generics.RetrieveAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated, CanViewUser]
    lookup_url_kwarg = "user_id"

    def get_queryset(self):
        return get_user_model().objects.prefetch_related("groups").order_by("id")


@extend_schema(
    summary="List groups",
    description="Return available user groups. Requires `auth.view_group`.",
    responses={
        status.HTTP_200_OK: GroupListSerializer(many=True),
        status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
        status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
    },
    tags=[GROUPS_TAG],
)
class GroupListView(generics.ListAPIView):
    queryset = Group.objects.order_by("name")
    serializer_class = GroupListSerializer
    permission_classes = [IsAuthenticated, CanViewGroup]


class AssignUserGroupView(APIView):
    permission_classes = [IsAuthenticated, CanAssignUserGroup]

    @extend_schema(
        summary="Assign user to group",
        description=(
            "Add an existing user to an existing group. Requires `auth.change_user`."
        ),
        request=AssignUserGroupSerializer,
        responses={
            status.HTTP_200_OK: UserDetailSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid group data."
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                description="User or group not found."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
        },
        tags=[USERS_TAG],
    )
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
