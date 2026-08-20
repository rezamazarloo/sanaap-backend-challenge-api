from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from document.exceptions import StorageUnavailable
from document.serializers import DocumentListSerializer, DocumentUploadSerializer
from document.services import DocumentService
from document.storage import ObjectStorageError


class DocumentListFilterMixin:
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "document_type": ["exact"],
        "document_type__code": ["exact", "iexact"],
        "content_type": ["exact", "iexact"],
        "created_at": ["gte", "lte"],
    }
    search_fields = ["original_filename"]
    ordering_fields = ["created_at", "updated_at", "size", "original_filename"]
    ordering = ["-created_at"]


class DocumentUploadMixin:
    def upload_document(
        self,
        request,
        *,
        user,
        response_serializer_class=DocumentListSerializer,
    ):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            document = DocumentService().upload_document(
                document_type=serializer.validated_data["document_type"],
                uploaded_file=serializer.validated_data["file"],
                user=user,
                uploaded_by=request.user,
                validated_upload=serializer.validated_data["validated_upload"],
            )
        except ObjectStorageError as exc:
            raise StorageUnavailable() from exc

        return Response(
            response_serializer_class(document).data,
            status=status.HTTP_201_CREATED,
        )
