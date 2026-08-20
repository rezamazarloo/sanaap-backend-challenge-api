from backoffice.document.serializers import (
    BackofficeDocumentDetailSerializer,
    BackofficeDocumentUploadSerializer,
)
from document.serializers import AllDocumentListSerializer, DocumentReplaceSerializer
from drf_spectacular.utils import (
    OpenApiRequest,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status

BACKOFFICE_DOCUMENTS_TAG = "Backoffice Documents"

UNAUTHORIZED_RESPONSE = OpenApiResponse(
    description="Authentication credentials were not provided or are invalid."
)
FORBIDDEN_RESPONSE = OpenApiResponse(
    description="The authenticated user does not have access to this resource."
)
NOT_FOUND_RESPONSE = OpenApiResponse(
    description="The requested resource was not found."
)

BACKOFFICE_DOCUMENT_UPLOAD_REQUEST = {
    "multipart/form-data": OpenApiRequest(
        request=BackofficeDocumentUploadSerializer,
        encoding={
            "file": {"contentType": "application/octet-stream"},
        },
    )
}
BACKOFFICE_DOCUMENT_REPLACE_REQUEST = {
    "multipart/form-data": OpenApiRequest(
        request=DocumentReplaceSerializer,
        encoding={
            "file": {"contentType": "application/octet-stream"},
        },
    )
}

BACKOFFICE_DOCUMENT_LIST_CREATE_SCHEMA = extend_schema_view(
    get=extend_schema(
        summary="List backoffice documents",
        description=(
            "Return all documents. Supports filtering by document/user fields. "
            "Requires `document.view_document`."
        ),
        responses={
            status.HTTP_200_OK: AllDocumentListSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
        },
        tags=[BACKOFFICE_DOCUMENTS_TAG],
    ),
    post=extend_schema(
        summary="Create backoffice document",
        description=(
            "Upload a document for the user provided by `user_id`. Requires "
            "`document.add_document`, or `document.add_image_document` when "
            "the target document type is image-only."
        ),
        request=BACKOFFICE_DOCUMENT_UPLOAD_REQUEST,
        responses={
            status.HTTP_201_CREATED: AllDocumentListSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid upload data."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
            status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
                description="Object storage is unavailable."
            ),
        },
        tags=[BACKOFFICE_DOCUMENTS_TAG],
    ),
)

BACKOFFICE_DOCUMENT_DETAIL_UPDATE_DELETE_SCHEMA = extend_schema_view(
    get=extend_schema(
        summary="Get backoffice document",
        description=(
            "Return full document details with a short-lived MinIO presigned URL. "
            "Requires `document.view_document`."
        ),
        responses={
            status.HTTP_200_OK: BackofficeDocumentDetailSerializer,
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
            status.HTTP_404_NOT_FOUND: NOT_FOUND_RESPONSE,
            status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
                description="Object storage is unavailable."
            ),
        },
        tags=[BACKOFFICE_DOCUMENTS_TAG],
    ),
    put=extend_schema(
        summary="Replace backoffice document file",
        description=(
            "Replace any user's document. Requires `document.change_document`, "
            "or `document.change_image_document` when both the existing and target "
            "document types are image-only."
        ),
        request=BACKOFFICE_DOCUMENT_REPLACE_REQUEST,
        responses={
            status.HTTP_200_OK: AllDocumentListSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid document data."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
            status.HTTP_404_NOT_FOUND: NOT_FOUND_RESPONSE,
            status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
                description="Object storage is unavailable."
            ),
        },
        tags=[BACKOFFICE_DOCUMENTS_TAG],
    ),
    delete=extend_schema(
        summary="Delete backoffice document",
        description="Delete any user's document. Requires `document.delete_document`.",
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
        tags=[BACKOFFICE_DOCUMENTS_TAG],
    ),
)
