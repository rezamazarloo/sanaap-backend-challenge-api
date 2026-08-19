import hashlib
from dataclasses import dataclass
from pathlib import Path

import filetype
from django.core.exceptions import ValidationError

EXTENSION_CONTENT_TYPES = {
    "csv": {"text/csv", "text/plain"},
    "gif": {"image/gif"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "pdf": {"application/pdf"},
    "png": {"image/png"},
    "txt": {"text/plain"},
    "webp": {"image/webp"},
}

EXTENSION_ALIASES = {
    "jpg": {"jpg", "jpeg"},
    "jpeg": {"jpg", "jpeg"},
}

TEXT_EXTENSIONS = {"csv", "txt"}
TEXT_EXTENSION_CONTENT_TYPES = {
    "csv": "text/csv",
    "txt": "text/plain",
}
SNIFF_BYTES = 8192


@dataclass(frozen=True)
class ValidatedUpload:
    original_filename: str
    extension: str
    content_type: str
    size: int
    checksum: str


class UploadedFileValidator:
    def validate(self, uploaded_file, document_type) -> ValidatedUpload:
        original_filename = Path(uploaded_file.name or "").name
        extension = self._get_extension(original_filename)
        allowed_extensions = self._allowed_extensions(document_type)

        if extension not in allowed_extensions:
            raise ValidationError(
                f"Extension '.{extension}' is not allowed for this document type."
            )

        size = getattr(uploaded_file, "size", 0)
        if size <= 0:
            raise ValidationError("Uploaded file must not be empty.")
        if size > document_type.max_size_bytes:
            raise ValidationError("Uploaded file exceeds the maximum allowed size.")

        head, checksum = self._inspect(uploaded_file)
        detected_extension, detected_content_type = self._detect_file_type(
            head,
            extension,
        )

        if not detected_content_type:
            raise ValidationError("Could not verify uploaded file type.")

        if detected_extension and not self._extensions_match(
            uploaded_extension=extension,
            detected_extension=detected_extension,
        ):
            raise ValidationError(
                "Uploaded file extension does not match the file content."
            )

        allowed_content_types = self._allowed_content_types(
            document_type,
            allowed_extensions,
        )
        if detected_content_type not in allowed_content_types:
            raise ValidationError(
                f"Content type '{detected_content_type}' is not allowed "
                "for this document type."
            )

        return ValidatedUpload(
            original_filename=original_filename,
            extension=extension,
            content_type=detected_content_type,
            size=size,
            checksum=checksum,
        )

    def _get_extension(self, filename):
        extension = Path(filename).suffix.lower().lstrip(".")
        if not extension:
            raise ValidationError("Uploaded file must have an extension.")
        return extension

    def _allowed_extensions(self, document_type):
        return {
            extension.lower().lstrip(".")
            for extension in document_type.allowed_extensions
        }

    def _allowed_content_types(self, document_type, allowed_extensions):
        configured_content_types = {
            content_type.lower()
            for content_type in document_type.allowed_content_types or []
        }
        if configured_content_types:
            return configured_content_types

        derived_content_types = set()
        for extension in allowed_extensions:
            derived_content_types.update(EXTENSION_CONTENT_TYPES.get(extension, set()))
        return derived_content_types

    def _inspect(self, uploaded_file):
        digest = hashlib.sha256()
        head = b""

        uploaded_file.seek(0)
        for chunk in uploaded_file.chunks():
            if len(head) < SNIFF_BYTES:
                remaining = SNIFF_BYTES - len(head)
                head += chunk[:remaining]
            digest.update(chunk)
        uploaded_file.seek(0)

        return head, digest.hexdigest()

    def _detect_file_type(self, head, extension):
        detected = filetype.guess(head)
        if detected:
            return detected.extension.lower(), detected.mime.lower()

        if extension in TEXT_EXTENSIONS and self._looks_like_text(head):
            return extension, TEXT_EXTENSION_CONTENT_TYPES[extension]

        return None, None

    def _extensions_match(self, uploaded_extension, detected_extension):
        aliases = EXTENSION_ALIASES.get(uploaded_extension, {uploaded_extension})
        return detected_extension in aliases

    def _looks_like_text(self, head):
        if b"\x00" in head:
            return False

        try:
            head.decode("utf-8")
        except UnicodeDecodeError:
            return False

        return True
