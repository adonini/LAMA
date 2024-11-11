#!/usr/bin/env bash

# Check for the correct number of arguments
if [ $# -ne 1 ]; then
    echo "Usage: $0 <DJANGO_BASE_PATH>"
    exit 1
fi

# Set the base path
DJANGO_BASE_PATH="${1}"

# Check the status of the Docker containers
echo "Checking status of Django Docker containers:"
if docker-compose -f ${DJANGO_BASE_PATH}/docker-compose.yaml ps; then
    echo ""
    echo "Status checked successfully."
else
    echo "Failed to check status."
    exit 1
fi