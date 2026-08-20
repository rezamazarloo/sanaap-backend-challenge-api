# sanaap-backend-challenge-api

Document Management System (DMS) with Django REST Framework

## Management Commands

Run migrations first so Django auth permissions exist:

```powershell
uv run python dms/manage.py migrate
```

Create a superuser:

```powershell
uv run python dms/manage.py createsuperuser
```

Create the default RBAC groups and permissions:

```powershell
uv run python dms/manage.py bootstrap_roles
```

Create the default `admin` / `admin` superuser:

```powershell
uv run python dms/manage.py create_default_superuser
```

Seed the initial document types:

```powershell
uv run python dms/manage.py seed_document_types
```

## Production Docker

The development `docker-compose.yml` is unchanged. Production uses nginx as the public reverse proxy and Gunicorn for Django:

```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

- `nginx` publishes the public ports and proxies to the private Docker upstreams.
- `app` builds the Django image, waits for healthy Postgres and MinIO, runs `migrate`, `bootstrap_roles`, `create_default_superuser`, and `seed_document_types`, then serves Gunicorn internally on port `8000`.
- Django is available through nginx on `http://localhost/`.
- MinIO S3 API is available through nginx on `http://localhost:9000/`.
- MinIO console is available through nginx on `http://localhost:9001/`.
- Docker Compose reads the existing `.env` file automatically.
- Swagger is available at `http://localhost/docs/` when `DJANGO_DEBUG=True`.
- In Docker, uploads use internal `MINIO_ENDPOINT=minio:9000`, while download links use `MINIO_PUBLIC_ENDPOINT`, defaulting to `localhost:9000`.

## Account API

- `POST /api/v1/account/auth/signup/` creates a public user account with `username` and `password`.
- `POST /api/v1/account/auth/login/` returns an authentication token for `username` and `password`.
- `POST /api/v1/account/auth/logout/` deletes the authenticated user's token.
- `GET /api/v1/account/users/` lists users; requires `auth.view_user`.
- `POST /api/v1/account/users/` creates a user; requires `auth.add_user`.
- `GET /api/v1/account/users/<user_id>/` returns one user with group membership; requires `auth.view_user`.
- `POST /api/v1/account/users/<user_id>/assign-group/` assigns a user to a group with `group_id`; requires `auth.change_user`.
- `GET /api/v1/account/groups/` lists available groups; requires `auth.view_group`.

## Document API

- `GET /api/v1/documents/` lists documents owned by the authenticated user.
- `POST /api/v1/documents/` uploads a document owned by the authenticated user.
- `GET /api/v1/documents/<document_id>/` returns metadata and a presigned download URL only when the document belongs to the authenticated user.
- `PUT /api/v1/documents/<document_id>/` replaces the authenticated user's own document.
- `DELETE /api/v1/documents/<document_id>/` deletes the authenticated user's own document.

## Backoffice Document API

- `GET /api/v1/backoffice/documents/` lists all documents and supports filtering by document/user fields; requires `document.view_document`.
- `POST /api/v1/backoffice/documents/` uploads a document for the `user_id` supplied in the request body; requires `document.add_document`, or `document.add_image_document` for image-only document types.
- `GET /api/v1/backoffice/documents/<document_id>/` returns full document details and a presigned download URL; requires `document.view_document`.
- `PUT /api/v1/backoffice/documents/<document_id>/` replaces any user's document; requires `document.change_document`, or `document.change_image_document` when both the current and target document types are image-only.
- `DELETE /api/v1/backoffice/documents/<document_id>/` deletes any user's document; requires `document.delete_document`.

## Document Type API

- `GET/POST /api/v1/documents/types/`
- `GET/PUT/DELETE /api/v1/documents/types/<document_type_id>/`
