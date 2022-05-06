#!/usr/bin/env bash

set -eo pipefail

# Use a lockfile to prevent overruns.
self=$(basename ${0})
exec {lockfile}>/var/lock/${self}
flock -n ${lockfile}
{

    # Environment variables should be loaded under all conditions.
    if [ -z "${TWLIGHT_HOME}" ]
    then
        exit 1
    fi

    PATH=/usr/local/bin:/usr/bin:/bin:/sbin:$PATH

    date=$(date +'%d.%H')

    ## Dump DB

    source ${TWLIGHT_HOME}/bin/twlight_mysqldump.sh

    echo "Backing up database and media"

    ## Perform backup
    tar -czf "${TWLIGHT_BACKUP_DIR}/${date}.tar.gz" -C "${TWLIGHT_MYSQLDUMP_DIR}" "./twlight.sql" -C "${TWLIGHT_HOME}" "./media"

    ## Root only
    chmod 0600 "${TWLIGHT_BACKUP_DIR}/${date}.tar.gz"

    echo "Finished TWLight backup."

    # Retain backups for 30 days.
    find "${TWLIGHT_BACKUP_DIR}" -name "*.tar.gz" -mtime +30 -delete || :

    echo "Removed backups created 30 days ago or more."
} {lockfile}>&-
