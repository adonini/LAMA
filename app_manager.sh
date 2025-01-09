#!/usr/bin/env bash

# Check for the correct number of arguments
if [ $# -ne 1 ]; then
    echo "Invalid number of arguments. Please run with '-h' option for available options. Exiting!"
    exit 1
fi

# Set the base path for Django project

DJANGO_BASE_PATH="/home/lst1/lama/LAMA"

# Define path scripts
BUILD_SCRIPT="${DJANGO_BASE_PATH}/build_image.sh"
START_SCRIPT="${DJANGO_BASE_PATH}/start_container.sh"
STOP_SCRIPT="${DJANGO_BASE_PATH}/stop_container.sh"
STATUS_SCRIPT="${DJANGO_BASE_PATH}/status_container.sh"

# Check if the base path is valid
if [ ! -d "${DJANGO_BASE_PATH}" ]; then
    echo "The base path '${DJANGO_BASE_PATH}' does not exist. Exiting!"
    exit 1
fi

# Loop over input options
case "$1" in
    -h|--help)
        echo "##############################    Django Docker Actions    ##############################"
        echo
        echo "   build    -- Builds the Docker image for the Django project"
        echo "   start          -- Launches the Django Docker containers"
        echo "   stop           -- Stops the Django Docker containers"
        echo "   status         -- Reports the status of the Django Docker containers"
        echo
        echo "#########################################################################################"
        exit 0
        ;;

    build)
        if [ -x "${BUILD_SCRIPT}" ]; then
            ${BUILD_SCRIPT} ${DJANGO_BASE_PATH}
        else
            echo "Build script '${BUILD_SCRIPT}' not found or not executable. Exiting!"
            exit 1
        fi
        ;;

    start)
        if [ -x "${START_SCRIPT}" ]; then
            ${START_SCRIPT} ${DJANGO_BASE_PATH}
        else
            echo "Start script '${START_SCRIPT}' not found or not executable. Exiting!"
            exit 1
        fi
        ;;

    stop)
        if [ -x "${STOP_SCRIPT}" ]; then
            ${STOP_SCRIPT} ${DJANGO_BASE_PATH}
        else
            echo "Stop script '${STOP_SCRIPT}' not found or not executable. Exiting!"
            exit 1
        fi
        ;;

    status)
        if [ -x "${STATUS_SCRIPT}" ]; then
            ${STATUS_SCRIPT} ${DJANGO_BASE_PATH}
        else
            echo "Status script '${STATUS_SCRIPT}' not found or not executable. Exiting!"
            exit 1
        fi
        ;;

    *)
        echo "Unknown command '$1'. Please run with '-h' option for available options. Exiting!"
        exit 1
        ;;
esac
