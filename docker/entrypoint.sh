#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py bootstrap_roles
python manage.py create_default_superuser
python manage.py seed_document_types

exec "$@"
