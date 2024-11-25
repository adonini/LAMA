#!/usr/bin/env bash

# Check for the correct number of arguments
if [ $# -ne 1 ]; then
    echo "Usage: $0 <DJANGO_BASE_PATH>"
    exit 1
fi

# Set the base path
DJANGO_BASE_PATH="${1}"

# Stop the Docker containers
echo "Stopping Django containers..."
if docker-compose -f ${DJANGO_BASE_PATH}/docker-compose.yaml down; then
    echo "Django containers stopped successfully."
else
    echo "Failed to stop Django containers."
    exit 1
fi