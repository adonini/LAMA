#!/bin/bash

# Load environment variables from .env file
set -a
source .env
set +a

# Wait for db to be up
echo "Waiting for postgres..."
while ! nc -z ${POSTGRES_HOST} ${POSTGRES_PORT}; do
  sleep 1
done
echo "PostgreSQL started"

# Run migrations
python3 manage.py migrate
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist
python3 manage.py shell <<EOF
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()
username = '${DJANGO_SUPERUSER_USERNAME}'
email = '${DJANGO_SUPERUSER_EMAIL}'
password = '${DJANGO_SUPERUSER_PASSWORD}'

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
EOF

# Start Django dev server
#exec python3 manage.py runserver 0.0.0.0:8000
# Start the Gunicorn server
exec gunicorn collaboration_manager.wsgi:application --bind 0.0.0.0:8000 --workers 3