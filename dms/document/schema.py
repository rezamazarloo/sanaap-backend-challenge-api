from document.serializers import (
    DocumentDownloadSerializer,
    DocumentListSerializer,
    DocumentReplaceSerializer,
    DocumentTypeSerializer,
    DocumentUploadAcceptedSerializer,
    DocumentUploadSerializer,
)
from drf_spectacular.utils import (
    OpenApiRequest,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status

DOCUMENTS_TAG = "Documents"
DOCUMENT_TYPES_TAG = "Document Types"

DOCUMENT_UPLOAD_REQUEST = {
    "multipart/form-data": OpenApiRequest(
        request=DocumentUploadSerializer,
        encoding={
            "file": {"contentType": "application/octet-stream"},
        },
    )
}
DOCUMENT_REPLACE_REQUEST = {
    "multipart/form-data": OpenApiRequest(
        request=DocumentReplaceSerializer,
        encoding={
            "file": {"contentType": "application/octet-stream"},
        },
    )
}

UNAUTHORIZED_RESPONSE = OpenApiResponse(
    description="Authentication credentials were not provided or are invalid."
)
FORBIDDEN_RESPONSE = OpenApiResponse(
    description="The authenticated user does not have access to this resource."
)
NOT_FOUND_RESPONSE = OpenApiResponse(
    description="The requested resource was not found."
)

DOCUMENT_LIST_CREATE_SCHEMA = extend_schema_view(
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
        description=(
            "Validate and stage a document for asynchronous upload to object storage."
        ),
        request=DOCUMENT_UPLOAD_REQUEST,
        responses={
            status.HTTP_202_ACCEPTED: DocumentUploadAcceptedSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid upload data."
            ),
            status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
        },
        tags=[DOCUMENTS_TAG],
    ),
)

DOCUMENT_DETAIL_UPDATE_DELETE_SCHEMA = extend_schema_view(
    get=extend_schema(
        summary="Generate document download URL",
        description=(
            "Return the document download state. Ready documents include a "
            "short-lived MinIO presigned URL."
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
        description=("Validate and stage a replacement file for asynchronous upload."),
        request=DOCUMENT_REPLACE_REQUEST,
        responses={
            status.HTTP_202_ACCEPTED: DocumentUploadAcceptedSerializer,
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

DOCUMENT_TYPE_LIST_CREATE_SCHEMA = extend_schema_view(
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

DOCUMENT_TYPE_DETAIL_UPDATE_DELETE_SCHEMA = extend_schema_view(
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
