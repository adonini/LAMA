#!/usr/bin/env bash

# Check for the correct number of arguments
if [ $# -eq 0 ]; then
    echo "No arguments supplied. You should provide the base path where the Django project is stored. Exiting!"
    exit 1
elif [ $# -gt 1 ]; then
    echo "Several arguments supplied. You should provide the base path where the Django project is stored. Exiting!"
    exit 1
fi

# Set the base path
DJANGO_BASE_PATH="${1}"

# Load environment variables from the .env file
if [ -f "${DJANGO_BASE_PATH}/.env" ]; then
    #export $(grep -v '^#' ${DJANGO_BASE_PATH}/.env | xargs)
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

export HOST_UID=$(id -u)
export HOST_GID=$(id -g)

# Build the Docker image
echo "Building Django Docker image with version ${PROJECT_VERSION}"
echo "Running command: docker build --build-arg HOST_UID=$HOST_UID --build-arg HOST_GID=$HOST_GID -f ${DJANGO_BASE_PATH}/Dockerfile . --tag django_lama:${PROJECT_VERSION}"
docker build --build-arg UID=$HOST_UID --build-arg GID=$HOST_GID --tag django_lama:${PROJECT_VERSION} -f ${DJANGO_BASE_PATH}/Dockerfile .
