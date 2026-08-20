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
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status

AUTH_TAG = "Authentication"
USERS_TAG = "Users"
GROUPS_TAG = "Groups"

UNAUTHORIZED_RESPONSE = OpenApiResponse(
    description="Authentication credentials were not provided or are invalid."
)
FORBIDDEN_RESPONSE = OpenApiResponse(
    description="The authenticated user does not have the required permission."
)
NOT_FOUND_RESPONSE = OpenApiResponse(
    description="The requested resource was not found."
)

SIGNUP_POST_SCHEMA = extend_schema(
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

LOGIN_POST_SCHEMA = extend_schema(
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

LOGOUT_POST_SCHEMA = extend_schema(
    summary="Log out",
    description="Delete the authenticated user's token.",
    request=None,
    responses={
        status.HTTP_204_NO_CONTENT: OpenApiResponse(description="Logged out."),
        status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
    },
    tags=[AUTH_TAG],
)

USER_LIST_CREATE_SCHEMA = extend_schema_view(
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

USER_DETAIL_SCHEMA = extend_schema(
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

GROUP_LIST_SCHEMA = extend_schema(
    summary="List groups",
    description="Return available user groups. Requires `auth.view_group`.",
    responses={
        status.HTTP_200_OK: GroupListSerializer(many=True),
        status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
        status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
    },
    tags=[GROUPS_TAG],
)

USER_GROUP_ASSIGN_POST_SCHEMA = extend_schema(
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
