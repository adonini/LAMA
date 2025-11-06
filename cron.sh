#!/bin/bash
set -Eeuo pipefail

week="$(date +%V)"
week=$((10#$week))
if ((week % 2)); then
    PROJECT_DIR="/home/lst1/lama/LAMA"
    {

        if [[ -f "${PROJECT_DIR%/}/.env" ]]; then
            set -a
            source "${PROJECT_DIR%/}/.env"
            set +a
            echo "PROJECT_VERSION=${PROJECT_VERSION:-<vacía>}"
        else
            echo "ERROR: ${PROJECT_DIR%/}/.env does not exists" >&2
            exit 1
        fi

        COMMAND="python manage.py runscript author_email_list"

        echo "docker version:"; /usr/bin/docker --version || true
        echo "docker ps:"; /usr/bin/docker ps || true

        CONTAINER_ID=$(/usr/bin/docker ps -q --filter "ancestor=django_lama:${PROJECT_VERSION}")
        echo "CONTAINER_ID=${CONTAINER_ID:-<>}"

        if [[ -z "$CONTAINER_ID" ]]; then
        echo "There is no running container using image django_lama:${PROJECT_VERSION}" >&2
        exit 1
        fi

        echo "This is the container id: $CONTAINER_ID"
        echo "Running command: $COMMAND"

        /usr/bin/docker exec -i "$CONTAINER_ID" $COMMAND

	echo "Checking if there is content on maildrop"
	MAILDROP="${PROJECT_DIR%/}/maildrop"

	if [[ -d "$MAILDROP" ]]; then
          shopt -s nullglob
          for f in "$MAILDROP"/*.mail; do
            echo "Sending mail from: $f"

	    TO="$(sed -n 's/^TO=//p' "$f" | head -n1)"
            FROM="$(sed -n 's/^FROM=//p' "$f" | head -n1)"
            SUBJECT="$(sed -n 's/^SUBJECT=//p' "$f" | head -n1)"

	    BODYFILE="$(mktemp)"
            awk 'found{print; next} /^$/{found=1}' "$f" > "$BODYFILE"

            MSGFILE="$(mktemp)"
            {
              printf 'From: %s\n' "$FROM"
              printf 'To: %s\n' "$TO"
              printf 'Subject: %s\n' "$SUBJECT"
              printf 'MIME-Version: 1.0\n'
              printf 'Content-Type: text/html; charset=UTF-8\n'
              printf '\n'
              cat "$BODYFILE"
            } > "$MSGFILE"

            if /usr/sbin/sendmail -t -f "$FROM" < "$MSGFILE"; then
              echo "Sent OK: $f"
            else
              echo "Send failed (deleted anyway): $f" >&2
            fi

            rm -f -- "$BODYFILE" "$MSGFILE" "$f"
          done
          shopt -u nullglob
        else
          echo "Maildrop not found: $MAILDROP"
        fi

    } >> "${PROJECT_DIR%/}/cron.log" 2>&1
fi
