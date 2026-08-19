from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter


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
