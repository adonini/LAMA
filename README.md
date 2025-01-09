# LAMA (LST MEMBERS AND AUTHORS MANAGER)

LAMA is a Django-based web application designed to manage and display statistics about members and authors across countries, groups, and institutes.
The app leverages LDAP authentication for secure user login with CTAO credentials and uses PostgreSQL as its database.
The application is fully containerized with Docker, using NGINX to serve static files and route traffic to the app.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Creating a Superuser](#creating-a-superuser)
- [LDAP Authentication](#ldap-authentication)
- [Serving Static Files](#serving-static-files)
- [Accessing PgAdmin](#accessing-pgadmin)
- [Managing Docker Containers](#managing-docker-containers)

## Features

- **Member and Author Management**: Track members and authors with advanced filtering.
- **Country, Group, and Institute Statistics**: Detailed metrics and percentages for all entities.
- **Historical Data**: Analyze trends with 12-month averages.
- **Interactive Filtering**: Filter data dynamically by country, group, and institute.
- **Visualizations**: Graphical summaries of members and authors over time.

## Prerequisites

Ensure you have the following installed on your machine:

- Docker
- Docker Compose

## Installation

1. **Clone the repository:**

   ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
   ```

2. **Create a .env file in the root directory:**

    ```bash
    cp .env.example .env
    ```

    Update the .env file with your environment-specific settings.
    To generate a django secret key for production:

    ```bash
    python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

3. **Build and run the containers:**

    ```bash
    docker-compose up --build
    ```

    This will start the following services:
    - PostgreSQL database
    - PgAdmin for database management
    - Django application
    - NGINX to serve static files and proxy requests

## Creating a Superuser

A Django superuser is automatically created during the first run using credentials from the .env file.
Ensure that `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` are set.

## LDAP Authentication

LAMA uses LDAP for authentication.
Users must log in with their CTAO nickname.
Only users in the lst-member LDAP group can access the app.
Configure LDAP settings in the .env file before running the app.

## Serving Static Files

Static files are collected during the build process and served by NGINX.
Ensure the NGINX configuration (nginx.conf) correctly points to the static files directory.

## Accessing PgAdmin

PgAdmin is available locally for database administration.
Use credentials from the .env file to log in.

## Managing Docker Containers

Use the provided scripts to manage the Docker containers:

- build_image.sh – Builds the Docker image.
- start_container.sh – Launches the Docker containers.
- stop_container.sh – Stops the Docker containers.
- status_container.sh – Reports the status of the Docker containers.

Before using the scripts, ensure they are executable.
You can make them executable with the following command:

```bash
    chmod +x ${DJANGO_BASE_PATH}/<script_name>.sh
```

Replace ${DJANGO_BASE_PATH} with the actual path where the scripts are located.

The ``app_manager.sh`` script unifies all the scripts above and simplifies container management:

```bash
    ./app_manager.sh <command>
```

Replace ``<command>`` with one of the following:

- build_image – Builds the Docker image.
- start – Starts the containers.
- stop – Stops the  containers.
- status – Displays the container status.
- -h or --help – Shows help.

Update the DJANGO_BASE_PATH variable in ``app_manager.sh`` to match your project path.
