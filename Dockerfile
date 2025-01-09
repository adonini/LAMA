FROM python:3

# set environment variables
# Python output is flushed immediately
# Prevent Python from writing .pyc files
ENV PYTHONBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LDAPTLS_CACERTDIR=/etc/ssl/certs/


# install system dependencies
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev \
    python3-dev \
    ldap-utils \
    iputils-ping \
    ca-certificates \
    dnsutils \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# set work directory
WORKDIR /code

# install dependencies
COPY ./requirements.txt /code/
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt

# Create the staticfiles directory
RUN mkdir -p /code/staticfiles

# copy project
COPY . /code/


# Change ownership of the work directory where the code is to the new user
RUN chown -R appmgr:appmgr /code

# # Switch to the new user
USER appmgr
WORKDIR /code

# Make the script executable
RUN chmod +x /code/run.sh
