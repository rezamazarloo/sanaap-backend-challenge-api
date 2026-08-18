from django.urls import path
from document.views import (
    AllDocumentListView,
    DocumentDetailView,
    DocumentListCreateView,
    DocumentTypeDetailView,
    DocumentTypeListCreateView,
    UserDocumentCreateView,
)

app_name = "document"

urlpatterns = [
    path(
        "types/", DocumentTypeListCreateView.as_view(), name="document-type-list-create"
    ),
    path(
        "types/<int:document_type_id>/",
        DocumentTypeDetailView.as_view(),
        name="document-type-detail",
    ),
    path("all/", AllDocumentListView.as_view(), name="document-all-list"),
    path(
        "users/<int:user_id>/",
        UserDocumentCreateView.as_view(),
        name="user-document-create",
    ),
    path("", DocumentListCreateView.as_view(), name="document-list-create"),
    path(
        "<int:document_id>/",
        DocumentDetailView.as_view(),
        name="document-detail",
    ),
]
