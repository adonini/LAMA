#!/bin/bash

# Set the base path to your Django project directory
DJANGO_BASE_PATH="/Users/alicedonini/Lavoro/LST/Members_manager/collaboration_manager"

# Load environment variables from .env
set -a
source "${DJANGO_BASE_PATH}/.env"
set +a

# Run Django management command to import members
docker-compose exec web python manage.py import_members