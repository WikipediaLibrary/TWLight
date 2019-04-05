#!/usr/bin/env bash

set -eo pipefail

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

PATH=/usr/local/bin:/usr/bin:/bin:/sbin:$PATH

echo "Dumping TWLight database"

## Perform sql-dump
bash -c "mysqldump -h '${DJANGO_DB_HOST}' -u '${DJANGO_DB_USER}' -p'${DJANGO_DB_PASSWORD}' '${DJANGO_DB_NAME}' > '${TWLIGHT_MYSQLDUMP_DIR}/twlight.sql'"

## Root only
chmod 0600 "${TWLIGHT_MYSQLDUMP_DIR}/twlight.sql"

echo "Finished dumping TWLight database."
