#!/usr/bin/env bash

if [  -z "$1" ]; then
    exit 1;
fi

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

PATH=/usr/local/bin:/usr/bin:/bin:/sbin:$PATH

mysqlimport_file=${1}

echo "Importing TWLight database"

## Drop existing DB.
bash -c "mysql -h '${DJANGO_DB_HOST}' -u '${DJANGO_DB_USER}' -p'${DJANGO_DB_PASSWORD}' -D '${DJANGO_DB_NAME}' -e 'DROP DATABASE ${DJANGO_DB_NAME}; CREATE DATABASE ${DJANGO_DB_NAME};'" | :

## Perform mysql import
bash -c "mysql -h '${DJANGO_DB_HOST}' -u '${DJANGO_DB_USER}' -p'${DJANGO_DB_PASSWORD}' -D '${DJANGO_DB_NAME}' < '${mysqlimport_file}'"

echo "Finished importing TWLight database."
