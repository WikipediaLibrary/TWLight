#!/usr/bin/env bash

if [  -z "$1" ]; then
    exit 1;
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
${TWLIGHT_HOME}/bin/twlight_mysqlimport.sh ${TWLIGHT_HOME}/twlight.sql

## Don't leave an extra DB dump laying out.
rm -f "${TWLIGHT_HOME}/twlight.sql"

## Set perms
chown -R ${TWLIGHT_UNIXNAME} "${TWLIGHT_HOME}"
find "${TWLIGHT_HOME}/media" -type f | xargs chmod 644

echo "Finished TWLight restore."
