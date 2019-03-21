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
mysqlhost=${DJANGO_DB_HOST}
mysqldb=twlight
mysqluser=twlight
mysqlpass=${MYSQL_PASSWORD}

echo "Importing TWLight database"

## Drop existing DB.
bash -c "mysql  -h '${mysqlhost}' -u '${mysqluser}' -p'${mysqlpass}' -D '${mysqldb}' -e 'DROP DATABASE ${mysqldb}; CREATE DATABASE ${mysqldb};'" | :

## Perform mysql import
bash -c "mysql  -h '${mysqlhost}' -u '${mysqluser}' -p'${mysqlpass}' -D '${mysqldb}' < '${mysqlimport_file}'"

echo "Finished importing TWLight database."
