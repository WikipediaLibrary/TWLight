#!/usr/bin/env bash

set -eo pipefail

# Environment variables should be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    exit 1
fi

# Get secrets.
if [ -z "${DJANGO_DB_PASSWORD}" ]
then
    source /app/bin/twlight_docker_secrets.sh
fi

PATH=/usr/local/bin:/usr/bin:/bin:/sbin:$PATH

if ${TWLIGHT_HOME}/bin/virtualenv_wait_for_db.sh
then
    echo "Dumping TWLight database"
    ## Perform sql-dump
    bash -c "mysqldump -h '${DJANGO_DB_HOST}' -u '${DJANGO_DB_USER}' -p'${DJANGO_DB_PASSWORD}' '${DJANGO_DB_NAME}' > '${TWLIGHT_MYSQLDUMP_DIR}/twlight.sql'"
    ## Root only
    chmod 0600 "${TWLIGHT_MYSQLDUMP_DIR}/twlight.sql"
    echo "Finished dumping TWLight database."
else
    exit 1
fi
