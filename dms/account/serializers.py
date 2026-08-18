from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)


class LoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField(read_only=True)


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = get_user_model()
        fields = ("username", "password")

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)


class SignupResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username")
        read_only_fields = fields
