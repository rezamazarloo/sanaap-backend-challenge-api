from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from document.models import Document, DocumentType
from document.serializers import DocumentTypeSerializer
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


class BackofficeDocumentListSerializer(serializers.ModelSerializer):
    document_type = DocumentTypeSerializer(read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    uploaded_by = serializers.StringRelatedField(read_only=True)
    uploaded_by_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Document
        fields = (
            "id",
            "document_type",
            "user",
            "user_id",
            "original_filename",
            "content_type",
            "size",
            "checksum",
            "uploaded_by",
            "uploaded_by_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class BackofficeDocumentDetailSerializer(BackofficeDocumentListSerializer):
    download_url = serializers.SerializerMethodField()
    expires_in = serializers.SerializerMethodField()

    class Meta(BackofficeDocumentListSerializer.Meta):
        fields = BackofficeDocumentListSerializer.Meta.fields + (
            "download_url",
            "expires_in",
        )

    def get_download_url(self, obj) -> str:
        return self.context["download_url"]

    def get_expires_in(self, obj) -> int:
        return self.context["expires_in"]
