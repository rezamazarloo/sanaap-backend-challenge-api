from django.urls import path
from document.views import (
    DocumentDetailUpdateDeleteView,
    DocumentListCreateView,
    DocumentTypeDetailUpdateDeleteView,
    DocumentTypeListCreateView,
)

app_name = "document"

urlpatterns = [
    path(
        "types/", DocumentTypeListCreateView.as_view(), name="document-type-list-create"
    ),
    path(
        "types/<int:document_type_id>/",
        DocumentTypeDetailUpdateDeleteView.as_view(),
        name="document-type-detail-update-delete",
    ),
    path("", DocumentListCreateView.as_view(), name="document-list-create"),
    path(
        "<int:document_id>/",
        DocumentDetailUpdateDeleteView.as_view(),
        name="document-detail-update-delete",
    ),
]
