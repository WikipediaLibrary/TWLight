#!/usr/bin/env bash

set -eo pipefail

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

PATH=/usr/local/bin:/usr/bin:/bin:/sbin:$PATH

mysqlhost=localhost
mysqldb=twlight
mysqluser=twlight
mysqlpass=$(cat ${TWLIGHT_HOME}/TWLight/settings/${TWLIGHT_ENV}_vars.py | grep ^MYSQL_PASSWORD | cut -d "=" -f 2 | xargs)

echo "Dumping TWLight database"

## Perform sql-dump
bash -c "mysqldump -h '${mysqlhost}' -u '${mysqluser}' -p'${mysqlpass}' '${mysqldb}' > '${TWLIGHT_MYSQLDUMP_DIR}/twlight.sql'"

## Root only
chmod 0600 "${TWLIGHT_MYSQLDUMP_DIR}/twlight.sql"

echo "Finished dumping TWLight database."
