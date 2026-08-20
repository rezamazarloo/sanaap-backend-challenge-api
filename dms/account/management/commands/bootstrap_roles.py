from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


ROLE_PERMISSION_SPECS = {
    "admin": [
        ("auth", "user", "add_user"),
        ("auth", "user", "change_user"),
        ("auth", "user", "view_user"),
        ("auth", "group", "view_group"),
        ("document", "document", "add_document"),
        ("document", "document", "change_document"),
        ("document", "document", "delete_document"),
        ("document", "document", "view_document"),
        ("document", "documenttype", "add_documenttype"),
        ("document", "documenttype", "change_documenttype"),
        ("document", "documenttype", "delete_documenttype"),
        ("document", "documenttype", "view_documenttype"),
    ],
    "editor": [
        ("document", "document", "add_image_document"),
        ("document", "document", "change_image_document"),
        ("document", "document", "view_document"),
    ],
    "viewer": [
        ("document", "document", "view_document"),
    ],
}


class Command(BaseCommand):
    help = "Create the default RBAC groups and group permissions."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._ensure_groups()

    def _ensure_groups(self):
        groups = {}

        for group_name, permission_specs in ROLE_PERMISSION_SPECS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            groups[group_name] = group

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created group '{group_name}'."))
            else:
                self.stdout.write(f"Group '{group_name}' already exists; skipped.")

            permissions = [self._get_permission(spec) for spec in permission_specs]
            existing_permission_ids = set(
                group.permissions.values_list("id", flat=True)
            )
            desired_permission_ids = {permission.id for permission in permissions}

            if existing_permission_ids != desired_permission_ids:
                group.permissions.set(permissions)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Set {len(permissions)} permission(s) for group "
                        f"'{group_name}'."
                    )
                )
            else:
                self.stdout.write(
                    f"Group '{group_name}' already has the expected permissions; "
                    "skipped."
                )

        return groups

    def _get_permission(self, spec):
        app_label, model, codename = spec

        try:
            return Permission.objects.select_related("content_type").get(
                content_type__app_label=app_label,
                content_type__model=model,
                codename=codename,
            )
        except Permission.DoesNotExist as exc:
            raise CommandError(
                f"Missing permission '{app_label}.{codename}'. "
                "Run migrations before running this command."
            ) from exc
