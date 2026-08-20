from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from document.models import DocumentType
from document.serializers import AllDocumentListSerializer
from document.validators import UploadedFileValidator
from rest_framework import serializers


class BackofficeDocumentUploadSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(),
        source="user",
        write_only=True,
    )
    document_type = serializers.PrimaryKeyRelatedField(
        queryset=DocumentType.objects.filter(is_active=True),
    )
    file = serializers.FileField(write_only=True)

    def validate(self, attrs):
        validator = UploadedFileValidator()

        try:
            attrs["validated_upload"] = validator.validate(
                uploaded_file=attrs["file"],
                document_type=attrs["document_type"],
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"file": exc.messages}) from exc

        return attrs


class BackofficeDocumentDetailSerializer(AllDocumentListSerializer):
    download_url = serializers.SerializerMethodField()
    expires_in = serializers.SerializerMethodField()

    class Meta(AllDocumentListSerializer.Meta):
        fields = AllDocumentListSerializer.Meta.fields + (
            "download_url",
            "expires_in",
        )

    def get_download_url(self, obj) -> str:
        return self.context["download_url"]

    def get_expires_in(self, obj) -> int:
        return self.context["expires_in"]
