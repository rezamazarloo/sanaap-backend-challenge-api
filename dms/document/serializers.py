from django.core.exceptions import ValidationError as DjangoValidationError
from document.models import Document, DocumentType
from document.validators import (
    EXTENSION_CONTENT_TYPES,
    UploadedFileValidator,
    content_types_for_extensions,
)
from rest_framework import serializers

AVAILABLE_EXTENSIONS = sorted(EXTENSION_CONTENT_TYPES)
AVAILABLE_CONTENT_TYPES = sorted(
    {
        content_type
        for content_types in EXTENSION_CONTENT_TYPES.values()
        for content_type in content_types
    }
)
EXTENSION_CONTENT_TYPE_HELP = "; ".join(
    f".{extension}: {', '.join(sorted(content_types))}"
    for extension, content_types in sorted(EXTENSION_CONTENT_TYPES.items())
)


class DocumentTypeSerializer(serializers.ModelSerializer):
    allowed_extensions = serializers.ListField(
        child=serializers.ChoiceField(choices=AVAILABLE_EXTENSIONS),
        help_text=(
            "Allowed file extensions for this document type. "
            f"Available values: {', '.join(AVAILABLE_EXTENSIONS)}."
        ),
    )
    allowed_content_types = serializers.ListField(
        child=serializers.ChoiceField(choices=AVAILABLE_CONTENT_TYPES),
        required=False,
        allow_empty=True,
        help_text=(
            "Allowed server-detected MIME types for this document type. "
            f"Available values by extension: {EXTENSION_CONTENT_TYPE_HELP}."
        ),
    )

    class Meta:
        model = DocumentType
        fields = (
            "id",
            "name",
            "code",
            "description",
            "allowed_extensions",
            "allowed_content_types",
            "max_size_bytes",
            "is_active",
        )
        read_only_fields = ("id",)

    def validate_allowed_extensions(self, value):
        extensions = [extension.lower().lstrip(".") for extension in value]
        if not extensions:
            raise serializers.ValidationError("At least one extension is required.")
        return sorted(set(extensions))

    def validate_allowed_content_types(self, value):
        return sorted({content_type.lower() for content_type in value})

    def validate_max_size_bytes(self, value):
        if value <= 0:
            raise serializers.ValidationError("Maximum size must be greater than zero.")
        return value

    def validate(self, attrs):
        allowed_extensions = attrs.get(
            "allowed_extensions",
            getattr(self.instance, "allowed_extensions", []),
        )
        if not allowed_extensions:
            raise serializers.ValidationError(
                {"allowed_extensions": "At least one extension is required."}
            )

        allowed_content_types = attrs.get(
            "allowed_content_types",
            getattr(self.instance, "allowed_content_types", []),
        )
        if allowed_content_types:
            related_content_types = content_types_for_extensions(allowed_extensions)
            unrelated_content_types = sorted(
                set(allowed_content_types) - related_content_types
            )
            if unrelated_content_types:
                raise serializers.ValidationError(
                    {
                        "allowed_content_types": (
                            "Content types must match the selected extensions. "
                            f"Invalid values: {', '.join(unrelated_content_types)}."
                        )
                    }
                )

            uncovered_extensions = [
                extension
                for extension in allowed_extensions
                if not (
                    EXTENSION_CONTENT_TYPES.get(extension, set())
                    & set(allowed_content_types)
                )
            ]
            if uncovered_extensions:
                raise serializers.ValidationError(
                    {
                        "allowed_content_types": (
                            "Each selected extension must have at least one related "
                            "content type. Missing content types for: "
                            f"{', '.join(uncovered_extensions)}."
                        )
                    }
                )

        return attrs


class UserDocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = (
            "id",
            "name",
            "code",
            "allowed_extensions",
            "max_size_bytes",
        )
        read_only_fields = fields


class DocumentListSerializer(serializers.ModelSerializer):
    document_type = UserDocumentTypeSerializer(read_only=True)

    class Meta:
        model = Document
        fields = (
            "id",
            "document_type",
            "original_filename",
            "content_type",
            "size",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AllDocumentListSerializer(serializers.ModelSerializer):
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


class DocumentUploadSerializer(serializers.Serializer):
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


class DocumentReplaceSerializer(serializers.Serializer):
    document_type = serializers.PrimaryKeyRelatedField(
        queryset=DocumentType.objects.filter(is_active=True),
        required=False,
    )
    file = serializers.FileField(write_only=True)

    def validate(self, attrs):
        document_type = attrs.get("document_type", self.instance.document_type)
        attrs["document_type"] = document_type
        validator = UploadedFileValidator()

        try:
            attrs["validated_upload"] = validator.validate(
                uploaded_file=attrs["file"],
                document_type=document_type,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"file": exc.messages}) from exc

        return attrs


class DocumentDownloadSerializer(DocumentListSerializer):
    download_url = serializers.SerializerMethodField()
    expires_in = serializers.SerializerMethodField()

    class Meta(DocumentListSerializer.Meta):
        fields = DocumentListSerializer.Meta.fields + (
            "download_url",
            "expires_in",
        )

    def get_download_url(self, obj) -> str:
        return self.context["download_url"]

    def get_expires_in(self, obj) -> int:
        return self.context["expires_in"]
