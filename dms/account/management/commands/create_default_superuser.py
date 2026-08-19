from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the default admin/admin superuser if it does not exist."

    def handle(self, *args, **options):
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(username="admin")

        if created:
            user.set_password("admin")
            user.is_active = True
            user.is_staff = True
            user.is_superuser = True
            user.save(
                update_fields=[
                    "password",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ]
            )
            self.stdout.write(self.style.SUCCESS("Created default admin superuser."))
        else:
            changed_fields = []
            if not user.is_active:
                user.is_active = True
                changed_fields.append("is_active")
            if not user.is_staff:
                user.is_staff = True
                changed_fields.append("is_staff")
            if not user.is_superuser:
                user.is_superuser = True
                changed_fields.append("is_superuser")

            if changed_fields:
                user.save(update_fields=changed_fields)
                self.stdout.write("Promoted existing 'admin' user to superuser.")
            else:
                self.stdout.write("Default admin superuser already exists; skipped.")

        admin_group = Group.objects.filter(name="admin").first()
        if admin_group:
            user.groups.add(admin_group)
