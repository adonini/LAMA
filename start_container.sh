#!/usr/bin/env bash

# Check for the correct number of arguments
if [ $# -ne 1 ]; then
    echo "Usage: $0 <DJANGO_BASE_PATH>"
    exit 1
fi

# Set the base path
DJANGO_BASE_PATH="${1}"

# Load environment variables from the .env file
if [ -f "${DJANGO_BASE_PATH}/.env" ]; then
    set -a
    source "${DJANGO_BASE_PATH}/.env"
    set +a
else
    echo "Could not find .env file in the specified base path. Exiting!"
    exit 1
fi

# Check if PROJECT_VERSION is set
if [ -z "$PROJECT_VERSION" ]; then
    echo "PROJECT_VERSION is not set in the .env file. Exiting!"
    exit 1
fi

# Bring up the Docker containers
echo "Bringing up Django Docker containers with version ${PROJECT_VERSION}"
if docker-compose -f ${DJANGO_BASE_PATH}/docker-compose.yaml --env-file ${DJANGO_BASE_PATH}/.env up -d; then
    echo "Django containers started successfully."
else
    echo "Failed to start Django containers."
    exit 1
fi
