from backoffice.document.serializers import (
    BackofficeDocumentAuditLogSerializer,
    BackofficeDocumentDetailSerializer,
    BackofficeDocumentListSerializer,
    BackofficeDocumentUploadSerializer,
)
from document.serializers import (
    DocumentReplaceSerializer,
    DocumentUploadAcceptedSerializer,
)
from drf_spectacular.utils import (
    OpenApiRequest,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status

BACKOFFICE_DOCUMENTS_TAG = "Backoffice Documents"
BACKOFFICE_DOCUMENT_AUDIT_LOGS_TAG = "Backoffice Document Audit Logs"

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
            status.HTTP_200_OK: BackofficeDocumentListSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
        },
        tags=[BACKOFFICE_DOCUMENTS_TAG],
    ),
    post=extend_schema(
        summary="Create backoffice document",
        description=(
            "Validate and stage a document for the user provided by `user_id`. "
            "The object storage upload runs asynchronously. Requires "
            "`document.add_document`, or `document.add_image_document` when the "
            "target document type is image-only."
        ),
        request=BACKOFFICE_DOCUMENT_UPLOAD_REQUEST,
        responses={
            status.HTTP_202_ACCEPTED: DocumentUploadAcceptedSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid upload data."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
        },
        tags=[BACKOFFICE_DOCUMENTS_TAG],
    ),
)

BACKOFFICE_DOCUMENT_DETAIL_UPDATE_DELETE_SCHEMA = extend_schema_view(
    get=extend_schema(
        summary="Get backoffice document",
        description=(
            "Return the document download state. Ready documents include a "
            "short-lived MinIO presigned URL. Requires `document.view_document`."
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
            "Validate and stage a replacement for any user's document. The object "
            "storage upload runs asynchronously. Requires `document.change_document`, "
            "or `document.change_image_document` when both the existing and target "
            "document types are image-only."
        ),
        request=BACKOFFICE_DOCUMENT_REPLACE_REQUEST,
        responses={
            status.HTTP_202_ACCEPTED: DocumentUploadAcceptedSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid document data."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
            status.HTTP_404_NOT_FOUND: NOT_FOUND_RESPONSE,
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

BACKOFFICE_DOCUMENT_AUDIT_LOG_LIST_SCHEMA = extend_schema_view(
    get=extend_schema(
        summary="List backoffice document audit logs",
        description=(
            "Return document audit logs. Supports filtering by `created_at`, "
            "`actor`, `action`, and `document`. Requires "
            "`document.view_documentauditlog`."
        ),
        responses={
            status.HTTP_200_OK: BackofficeDocumentAuditLogSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
            status.HTTP_403_FORBIDDEN: FORBIDDEN_RESPONSE,
        },
        tags=[BACKOFFICE_DOCUMENT_AUDIT_LOGS_TAG],
    ),
)
