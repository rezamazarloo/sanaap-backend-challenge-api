from django.db.models.deletion import ProtectedError
from document.exceptions import StorageUnavailable
from document.mixins import DocumentListFilterMixin, DocumentUploadMixin
from document.models import Document, DocumentType
from document.pagination import DocumentPagination
from document.permissions import DocumentTypePermission
from document.schema import (
    DOCUMENT_DETAIL_UPDATE_DELETE_SCHEMA,
    DOCUMENT_LIST_CREATE_SCHEMA,
    DOCUMENT_TYPE_DETAIL_UPDATE_DELETE_SCHEMA,
    DOCUMENT_TYPE_LIST_CREATE_SCHEMA,
)
from document.serializers import (
    DocumentDownloadSerializer,
    DocumentListSerializer,
    DocumentReplaceSerializer,
    DocumentTypeSerializer,
    DocumentUploadSerializer,
)
from document.services import DocumentService
from document.storage import ObjectStorageError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@DOCUMENT_LIST_CREATE_SCHEMA
class DocumentListCreateView(
    DocumentUploadMixin,
    DocumentListFilterMixin,
    ListCreateAPIView,
):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    pagination_class = DocumentPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Document.objects.none()

        return Document.objects.select_related("document_type").filter(
            user=self.request.user
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DocumentUploadSerializer
        return DocumentListSerializer

    def post(self, request, *args, **kwargs):
        return self.upload_document(request, user=request.user)


@DOCUMENT_DETAIL_UPDATE_DELETE_SCHEMA
class DocumentDetailUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "document_id"
    http_method_names = ["get", "put", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Document.objects.none()

        return Document.objects.select_related("document_type").filter(
            user=self.request.user
        )

    def get_serializer_class(self):
        if self.request.method == "PUT":
            return DocumentReplaceSerializer
        return DocumentDownloadSerializer

    def retrieve(self, request, *args, **kwargs):
        document = self.get_object()
        service = DocumentService()

        try:
            download_url = service.generate_download_url(document)
        except ObjectStorageError as exc:
            raise StorageUnavailable() from exc

        serializer = self.get_serializer(
            document,
            context={
                "download_url": download_url,
                "expires_in": service.download_expiration,
            },
        )
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        document = self.get_object()
        serializer = self.get_serializer(document, data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            document = DocumentService().replace_document(
                document=document,
                document_type=serializer.validated_data["document_type"],
                uploaded_file=serializer.validated_data["file"],
                uploaded_by=request.user,
                validated_upload=serializer.validated_data["validated_upload"],
            )
        except ObjectStorageError as exc:
            raise StorageUnavailable() from exc

        return Response(DocumentListSerializer(document).data)

    def destroy(self, request, *args, **kwargs):
        document = self.get_object()

        try:
            DocumentService().delete_document(document)
        except ObjectStorageError as exc:
            raise StorageUnavailable() from exc

        return Response(status=status.HTTP_204_NO_CONTENT)


@DOCUMENT_TYPE_LIST_CREATE_SCHEMA
class DocumentTypeListCreateView(ListCreateAPIView):
    queryset = DocumentType.objects.order_by("name")
    serializer_class = DocumentTypeSerializer
    permission_classes = [IsAuthenticated, DocumentTypePermission]


@DOCUMENT_TYPE_DETAIL_UPDATE_DELETE_SCHEMA
class DocumentTypeDetailUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    queryset = DocumentType.objects.order_by("name")
    serializer_class = DocumentTypeSerializer
    permission_classes = [IsAuthenticated, DocumentTypePermission]
    lookup_url_kwarg = "document_type_id"
    http_method_names = ["get", "put", "delete", "head", "options"]

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError as exc:
            raise ValidationError(
                {"detail": "Document type is used by existing documents."}
            ) from exc
