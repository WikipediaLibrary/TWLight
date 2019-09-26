#!/usr/bin/env bash

if [  -z "$1" ]; then
    echo "Please specify a backup file."
    exit 1
fi

# Environment variables should be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    exit 1
fi

PATH=/usr/local/bin:/usr/bin:/bin:/sbin:$PATH

restore_file=${1}

## Extract tarball
tar -xvzf  "${restore_file}" -C "${TWLIGHT_HOME}" --no-overwrite-dir

## Import DB
if ${TWLIGHT_HOME}/bin/virtualenv_wait_for_db.sh
then
    ${TWLIGHT_HOME}/bin/twlight_mysqlimport.sh ${TWLIGHT_HOME}/twlight.sql
fi
## Don't leave an extra DB dump laying out.
rm -f "${TWLIGHT_HOME}/twlight.sql"

## Set perms
chown -R ${TWLIGHT_UNIXNAME} "${TWLIGHT_HOME}"
find "${TWLIGHT_HOME}/media" -type f | xargs chmod 644

## Run any necessary DB operations.
${TWLIGHT_HOME}/bin/virtualenv_migrate.sh

echo "Finished TWLight restore."
