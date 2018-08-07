#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

PATH=/usr/local/bin:/usr/bin:/bin:/sbin:$PATH

date=$(date +'%d.%H')

## Dump DB
source ${TWLIGHT_HOME}/bin/twlight_mysqldump.sh || exit 1

echo "Backing up database and media"

## Perform backup
tar -czf "${TWLIGHT_BACKUP_DIR}/${date}.tar.gz" -C "${TWLIGHT_MYSQLDUMP_DIR}" "./twlight.sql" -C "${TWLIGHT_HOME}" "./media" || exit 1

## Root only
chmod 0600 "${TWLIGHT_BACKUP_DIR}/${date}.tar.gz" || exit 1

echo "Finished TWLight backup."
