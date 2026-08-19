from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from document.mixins import DocumentListFilterMixin
from document.models import Document, DocumentType
from document.pagination import DocumentPagination
from document.permissions import (
    CanAddDocument,
    CanViewDocuments,
    DocumentPermission,
    DocumentTypePermission,
)
from document.serializers import (
    AllDocumentListSerializer,
    DocumentDownloadSerializer,
    DocumentListSerializer,
    DocumentReplaceSerializer,
    DocumentTypeSerializer,
    DocumentUploadSerializer,
)
from document.services import DocumentService
from document.storage import ObjectStorageError
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

DOCUMENTS_TAG = "Documents"
DOCUMENT_TYPES_TAG = "Document Types"

UNAUTHORIZED_RESPONSE = OpenApiResponse(
    description="Authentication credentials were not provided or are invalid."
)
FORBIDDEN_RESPONSE = OpenApiResponse(
    description="The authenticated user does not have access to this resource."
)
NOT_FOUND_RESPONSE = OpenApiResponse(
    description="The requested resource was not found."
)


class StorageUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Object storage is temporarily unavailable."
    default_code = "object_storage_unavailable"


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


@extend_schema_view(
    get=extend_schema(
        summary="List documents",
        description="Return documents owned by the authenticated user.",
        responses={
            status.HTTP_200_OK: DocumentListSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
        },
        tags=[DOCUMENTS_TAG],
    ),
    post=extend_schema(
        summary="Upload document",
        description="Upload a document for the authenticated user.",
        request=DocumentUploadSerializer,
        responses={
            status.HTTP_201_CREATED: DocumentListSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid upload data."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
                description="Object storage is unavailable."
            ),
        },
        tags=[DOCUMENTS_TAG],
    ),
)
class DocumentListCreateView(
    DocumentUploadMixin,
    DocumentListFilterMixin,
    generics.ListCreateAPIView,
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


@extend_schema(
    summary="List all documents",
    description="Return all documents. Requires `document.view_document`.",
    responses={
        status.HTTP_200_OK: AllDocumentListSerializer(many=True),
        status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
        status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
    },
    tags=[DOCUMENTS_TAG],
)
class AllDocumentListView(DocumentListFilterMixin, generics.ListAPIView):
    serializer_class = AllDocumentListSerializer
    permission_classes = [IsAuthenticated, CanViewDocuments]
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


@extend_schema_view(
    post=extend_schema(
        summary="Upload document for user",
        description=(
            "Upload a document owned by a specific user. "
            "Requires `document.add_document`."
        ),
        request=DocumentUploadSerializer,
        responses={
            status.HTTP_201_CREATED: AllDocumentListSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid upload data."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
            status.HTTP_404_NOT_FOUND: NOT_FOUND_RESPONSE,
            status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
                description="Object storage is unavailable."
            ),
        },
        tags=[DOCUMENTS_TAG],
    ),
)
class UserDocumentCreateView(DocumentUploadMixin, generics.CreateAPIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, CanAddDocument]
    serializer_class = DocumentUploadSerializer
    lookup_url_kwarg = "user_id"
    http_method_names = ["post", "options"]

    def post(self, request, *args, **kwargs):
        user = self._get_target_user()
        return self.upload_document(
            request,
            user=user,
            response_serializer_class=AllDocumentListSerializer,
        )

    def _get_target_user(self):
        return get_object_or_404(
            get_user_model().objects.all(),
            pk=self.kwargs[self.lookup_url_kwarg],
        )


@extend_schema_view(
    get=extend_schema(
        summary="Generate document download URL",
        description=(
            "Return document metadata with a short-lived MinIO presigned URL."
        ),
        responses={
            status.HTTP_200_OK: DocumentDownloadSerializer,
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
            status.HTTP_404_NOT_FOUND: NOT_FOUND_RESPONSE,
            status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
                description="Object storage is unavailable."
            ),
        },
        tags=[DOCUMENTS_TAG],
    ),
    put=extend_schema(
        summary="Replace document file",
        description=(
            "Upload a replacement file for an existing document. Owners can replace "
            "their own documents; other documents require `document.change_document`."
        ),
        request=DocumentReplaceSerializer,
        responses={
            status.HTTP_200_OK: DocumentListSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid document data."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
            status.HTTP_404_NOT_FOUND: NOT_FOUND_RESPONSE,
        },
        tags=[DOCUMENTS_TAG],
    ),
    delete=extend_schema(
        summary="Delete document",
        description="Delete the object from MinIO and remove the database record.",
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description="Document deleted."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
            status.HTTP_404_NOT_FOUND: NOT_FOUND_RESPONSE,
            status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
                description="Object storage is unavailable."
            ),
        },
        tags=[DOCUMENTS_TAG],
    ),
)
class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, DocumentPermission]
    lookup_url_kwarg = "document_id"
    http_method_names = ["get", "put", "delete", "head", "options"]

    def get_queryset(self):
        return Document.objects.select_related("document_type", "uploaded_by", "user")

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


@extend_schema_view(
    get=extend_schema(
        summary="List document types",
        responses={
            status.HTTP_200_OK: DocumentTypeSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
        },
        tags=[DOCUMENT_TYPES_TAG],
    ),
    post=extend_schema(
        summary="Create document type",
        request=DocumentTypeSerializer,
        responses={
            status.HTTP_201_CREATED: DocumentTypeSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid document type data."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
        },
        tags=[DOCUMENT_TYPES_TAG],
    ),
)
class DocumentTypeListCreateView(generics.ListCreateAPIView):
    queryset = DocumentType.objects.order_by("name")
    serializer_class = DocumentTypeSerializer
    permission_classes = [IsAuthenticated, DocumentTypePermission]


@extend_schema_view(
    get=extend_schema(
        summary="Get document type",
        responses={
            status.HTTP_200_OK: DocumentTypeSerializer,
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
            status.HTTP_404_NOT_FOUND: NOT_FOUND_RESPONSE,
        },
        tags=[DOCUMENT_TYPES_TAG],
    ),
    put=extend_schema(
        summary="Update document type",
        request=DocumentTypeSerializer,
        responses={
            status.HTTP_200_OK: DocumentTypeSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid document type data."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
            status.HTTP_404_NOT_FOUND: NOT_FOUND_RESPONSE,
        },
        tags=[DOCUMENT_TYPES_TAG],
    ),
    delete=extend_schema(
        summary="Delete document type",
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description="Document type deleted."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
            status.HTTP_404_NOT_FOUND: NOT_FOUND_RESPONSE,
        },
        tags=[DOCUMENT_TYPES_TAG],
    ),
)
class DocumentTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
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
