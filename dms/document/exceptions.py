from rest_framework import status
from rest_framework.exceptions import APIException


class StorageUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Object storage is temporarily unavailable."
    default_code = "object_storage_unavailable"
