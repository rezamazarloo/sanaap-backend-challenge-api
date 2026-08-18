from account.serializers import (
    LoginResponseSerializer,
    LoginSerializer,
    SignupResponseSerializer,
    SignupSerializer,
)
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class SignupView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        auth=[],
        request=SignupSerializer,
        responses={
            status.HTTP_201_CREATED: SignupResponseSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid signup data."
            ),
        },
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
        request=LoginSerializer,
        responses={
            status.HTTP_200_OK: LoginResponseSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid username or password."
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="Logged out.")
        },
    )
    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
