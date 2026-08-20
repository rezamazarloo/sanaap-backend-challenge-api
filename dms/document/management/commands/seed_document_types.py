from django.core.management.base import BaseCommand
from document.models import DocumentType

INITIAL_DOCUMENT_TYPES = [
    {
        "name": "National ID Card",
        "code": "national_id_card",
        "description": "Government-issued national identification card.",
        "allowed_extensions": ["jpg", "jpeg", "png", "webp"],
        "allowed_content_types": ["image/jpeg", "image/png", "image/webp"],
        "max_size_bytes": 5 * 1024 * 1024,
        "is_active": True,
    },
    {
        "name": "Profile",
        "code": "profile",
        "description": "Personal profile image.",
        "allowed_extensions": ["jpg", "jpeg", "png", "webp"],
        "allowed_content_types": ["image/jpeg", "image/png", "image/webp"],
        "max_size_bytes": 5 * 1024 * 1024,
        "is_active": True,
    },
]


class Command(BaseCommand):
    help = "Create initial document types when they do not already exist."

    def handle(self, *args, **options):
        for document_type_data in INITIAL_DOCUMENT_TYPES:
            document_type, created = DocumentType.objects.get_or_create(
                code=document_type_data["code"],
                defaults=document_type_data,
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created document type '{document_type.name}'.")
                )
            elif not document_type.allowed_content_types:
                document_type.allowed_content_types = document_type_data[
                    "allowed_content_types"
                ]
                document_type.save(update_fields=["allowed_content_types"])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated document type '{document_type.name}'."
                    )
                )
            else:
                self.stdout.write(
                    f"Document type '{document_type.name}' already exists; skipped."
                )
