#!/bin/sh
set -eu

python dms/manage.py migrate --noinput
python dms/manage.py bootstrap_roles
python dms/manage.py seed_document_types

exec "$@"
