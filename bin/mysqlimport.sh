#!/usr/bin/env bash

set -eo pipefail

# Environment variables should be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    exit 1
fi

PATH=/usr/local/bin:/usr/bin:/bin:/sbin:$PATH

echo "Importing TWLight database"

mysql_cmd=(mysql -h "${DJANGO_DB_HOST}" -u "${DJANGO_DB_USER}" -p"${DJANGO_DB_PASSWORD}")

## Drop existing DB. IF EXISTS so a first-time import isn't a failure.
"${mysql_cmd[@]}" -e "DROP DATABASE IF EXISTS ${DJANGO_DB_NAME}; CREATE DATABASE ${DJANGO_DB_NAME};"

## Import the dump streamed on stdin.
"${mysql_cmd[@]}" -D "${DJANGO_DB_NAME}"

echo "Finished importing TWLight database."
