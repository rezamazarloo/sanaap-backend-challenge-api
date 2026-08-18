from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class AccountManagementAPITests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="admin",
            password="StrongPass123!",
        )
        self.admin.user_permissions.add(
            self._permission("auth", "user", "add_user"),
            self._permission("auth", "user", "change_user"),
            self._permission("auth", "user", "view_user"),
            self._permission("auth", "group", "view_group"),
        )

        self.regular_user = get_user_model().objects.create_user(
            username="regular",
            password="StrongPass123!",
        )
        self.target_user = get_user_model().objects.create_user(
            username="target",
            password="StrongPass123!",
        )
        self.editor_group = Group.objects.create(name="editor")

    def _permission(self, app_label, model, codename):
        return Permission.objects.get(
            content_type__app_label=app_label,
            content_type__model=model,
            codename=codename,
        )

    def test_user_list_create_and_detail_require_django_permissions(self):
        self.client.force_authenticate(self.admin)

        list_response = self.client.get(reverse("account:user-list"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 3)
        self.assertEqual(set(list_response.data[0].keys()), {"id", "username"})

        create_response = self.client.post(
            reverse("account:user-list"),
            {
                "username": "new-user",
                "password": "StrongPass123!",
                "email": "new-user@example.com",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", create_response.data)

        user = get_user_model().objects.get(username="new-user")
        detail_response = self.client.get(
            reverse("account:user-detail", kwargs={"user_id": user.pk})
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["username"], "new-user")
        self.assertIn("groups", detail_response.data)

        self.client.force_authenticate(self.regular_user)
        forbidden_response = self.client.get(reverse("account:user-list"))
        self.assertEqual(forbidden_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_list_and_user_group_assignment(self):
        self.client.force_authenticate(self.admin)

        list_response = self.client.get(reverse("account:group-list"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]["name"], "editor")

        assign_response = self.client.post(
            reverse(
                "account:user-assign-group",
                kwargs={"user_id": self.target_user.pk},
            ),
            {"group_id": self.editor_group.pk},
            format="json",
        )
        self.assertEqual(assign_response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.target_user.groups.filter(name="editor").exists())
