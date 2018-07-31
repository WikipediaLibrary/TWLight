#!/usr/bin/env bash

if [  -z "$1" ]; then
    exit 1;
fi

PATH=/usr/local/bin:/usr/bin:/bin:/sbin:$PATH

mysqlimport_file=${1}
mysqlhost=localhost
mysqldb=twlight
mysqluser=twlight
mysqlpass=$(cat ${TWLIGHT_HOME}/TWLight/settings/${TWLIGHT_ENV}_vars.py | grep ^MYSQL_PASSWORD | cut -d "=" -f 2 | xargs)

echo "Importing TWLight database"

## Perform mysql import
bash -c "mysql  -h '${mysqlhost}' -u '${mysqluser}' -p'${mysqlpass}' -D '${mysqldb}' < '${mysqlimport_file}'"

echo "Finished importing TWLight database."
