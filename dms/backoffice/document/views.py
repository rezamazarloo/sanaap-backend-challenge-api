from backoffice.document.permissions import BackofficeDocumentPermission
from backoffice.document.schema import (
    BACKOFFICE_DOCUMENT_DETAIL_UPDATE_DELETE_SCHEMA,
    BACKOFFICE_DOCUMENT_LIST_CREATE_SCHEMA,
)
from backoffice.document.serializers import (
    BackofficeDocumentDetailSerializer,
    BackofficeDocumentUploadSerializer,
)
from document.exceptions import StorageUnavailable
from document.mixins import DocumentListFilterMixin
from document.models import Document
from document.pagination import DocumentPagination
from document.serializers import AllDocumentListSerializer, DocumentReplaceSerializer
from document.services import DocumentService
from document.storage import ObjectStorageError
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
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
        return AllDocumentListSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            document = DocumentService().upload_document(
                document_type=serializer.validated_data["document_type"],
                uploaded_file=serializer.validated_data["file"],
                user=serializer.validated_data["user"],
                uploaded_by=request.user,
                validated_upload=serializer.validated_data["validated_upload"],
            )
        except ObjectStorageError as exc:
            raise StorageUnavailable() from exc

        return Response(
            AllDocumentListSerializer(document).data,
            status=status.HTTP_201_CREATED,
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

        return Response(AllDocumentListSerializer(document).data)

    def destroy(self, request, *args, **kwargs):
        document = self.get_object()

        try:
            DocumentService().delete_document(document)
        except ObjectStorageError as exc:
            raise StorageUnavailable() from exc

        return Response(status=status.HTTP_204_NO_CONTENT)
