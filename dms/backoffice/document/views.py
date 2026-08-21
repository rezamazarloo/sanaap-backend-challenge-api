from backoffice.document.pagination import BackofficeDocumentAuditLogPagination
from backoffice.document.permissions import (
    BackofficeDocumentAuditLogPermission,
    BackofficeDocumentPermission,
)
from backoffice.document.schema import (
    BACKOFFICE_DOCUMENT_AUDIT_LOG_LIST_SCHEMA,
    BACKOFFICE_DOCUMENT_DETAIL_UPDATE_DELETE_SCHEMA,
    BACKOFFICE_DOCUMENT_LIST_CREATE_SCHEMA,
)
from backoffice.document.serializers import (
    BackofficeDocumentAuditLogSerializer,
    BackofficeDocumentDetailSerializer,
    BackofficeDocumentListSerializer,
    BackofficeDocumentUploadSerializer,
)
from django_filters.rest_framework import DjangoFilterBackend
from document.exceptions import StorageUnavailable
from document.mixins import DocumentListFilterMixin
from document.models import Document, DocumentAuditLog, DocumentStatus
from document.pagination import DocumentPagination
from document.serializers import (
    DocumentReplaceSerializer,
    DocumentUploadAcceptedSerializer,
)
from document.services import DocumentService
from document.storage import ObjectStorageError
from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@BACKOFFICE_DOCUMENT_LIST_CREATE_SCHEMA
class BackofficeDocumentListCreateView(
    DocumentListFilterMixin,
    ListCreateAPIView,
):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, BackofficeDocumentPermission]
    pagination_class = DocumentPagination
    filterset_fields = {
        **DocumentListFilterMixin.filterset_fields,
        "user": ["exact"],
        "uploaded_by": ["exact"],
    }

    def get_queryset(self):
        return Document.objects.select_related(
            "document_type",
            "uploaded_by",
            "user",
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BackofficeDocumentUploadSerializer
        return BackofficeDocumentListSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document = DocumentService().upload_document(
            document_type=serializer.validated_data["document_type"],
            uploaded_file=serializer.validated_data["file"],
            user=serializer.validated_data["user"],
            uploaded_by=request.user,
            validated_upload=serializer.validated_data["validated_upload"],
        )

        return Response(
            DocumentUploadAcceptedSerializer(document).data,
            status=status.HTTP_202_ACCEPTED,
        )


@BACKOFFICE_DOCUMENT_DETAIL_UPDATE_DELETE_SCHEMA
class BackofficeDocumentDetailUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, BackofficeDocumentPermission]
    lookup_url_kwarg = "document_id"
    http_method_names = ["get", "put", "delete", "head", "options"]

    def get_queryset(self):
        return Document.objects.select_related("document_type", "uploaded_by", "user")

    def get_serializer_class(self):
        if self.request.method == "PUT":
            return DocumentReplaceSerializer
        return BackofficeDocumentDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        document = self.get_object()
        service = DocumentService()
        context = {}

        if document.status == DocumentStatus.READY:
            try:
                context = {
                    "download_url": service.generate_download_url(
                        document,
                        actor=request.user,
                    ),
                    "expires_in": service.download_expiration,
                }
            except ObjectStorageError as exc:
                raise StorageUnavailable() from exc

        serializer = self.get_serializer(
            document,
            context=context,
        )
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        document = self.get_object()
        serializer = self.get_serializer(document, data=request.data)
        serializer.is_valid(raise_exception=True)

        document = DocumentService().replace_document(
            document=document,
            document_type=serializer.validated_data["document_type"],
            uploaded_file=serializer.validated_data["file"],
            uploaded_by=request.user,
            validated_upload=serializer.validated_data["validated_upload"],
        )

        return Response(
            DocumentUploadAcceptedSerializer(document).data,
            status=status.HTTP_202_ACCEPTED,
        )

    def destroy(self, request, *args, **kwargs):
        document = self.get_object()

        try:
            DocumentService().delete_document(document, actor=request.user)
        except ObjectStorageError as exc:
            raise StorageUnavailable() from exc

        return Response(status=status.HTTP_204_NO_CONTENT)


@BACKOFFICE_DOCUMENT_AUDIT_LOG_LIST_SCHEMA
class BackofficeDocumentAuditLogListView(ListAPIView):
    serializer_class = BackofficeDocumentAuditLogSerializer
    permission_classes = [IsAuthenticated, BackofficeDocumentAuditLogPermission]
    pagination_class = BackofficeDocumentAuditLogPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        "created_at": ["gte", "lte"],
        "actor": ["exact"],
        "action": ["exact"],
        "document": ["exact"],
    }
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return DocumentAuditLog.objects.select_related("actor", "document")
