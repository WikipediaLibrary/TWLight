#!/usr/bin/env bash
set -eo pipefail

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

{

    # print the date for logging purposes
    echo [$(date)]

    # Must run as root.
    if [ "${USER}" != "root" ]
    then
        echo "twlight_update.sh must be run as root!"
        exit 1
    fi

    # init is basically a --force flag.
    if [ "${1}" = "init" ]
    then
         init="true"
    fi

    git_check() {
        # Verify that the unix user can talk to the remote.
        cd ${TWLIGHT_HOME}
        if git fetch --dry-run
        then

        # Check the remote status.
        git fetch

        # Only do stuff if we're behind the remote. Cribbed from stackoverflow:
        # https://stackoverflow.com/a/3278427
        upstream=${1:-'@{u}'}
        local=$(git rev-parse @)
        remote=$(git rev-parse "$upstream")
        base=$(git merge-base @ "$upstream")

        if [ "${local}" = "${remote}" ]
        then
            echo "Up-to-date"
            exit 0
        elif [ "${local}" = "${base}" ]
        then
            echo "Need to pull"
            return 0
        elif [ "${remote}" = "${base}" ]
        then
            echo "Need to push"
            return 1
        else
            echo "Diverged"
            return 1
        fi
    }

    git_pull() {

        # Backup production before making changes.
        if [ "${TWLIGHT_ENV}" = "production" ]
        then
            ${TWLIGHT_HOME}/bin/./twlight_backup.sh
        fi

        # Pull latest code from ${TWLIGHT_GIT_REVISION}.
        cd ${TWLIGHT_HOME}
        git pull ${TWLIGHT_GIT_REVISION}

        # Make sure ${TWLIGHT_UNIXNAME} owns everything.
        chown -R ${TWLIGHT_UNIXNAME}:${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}
    }

    virtualenv_update() {
        # Update pip dependencies.
        sudo su ${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/bin/virtualenv_pip_update.sh

        # Process static assets.
        sudo su ${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/bin/virtualenv_clearstatic.sh

        # Run migrations.
        sudo su ${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/bin/virtualenv_migrate.sh

        # Compile translations.
        sudo su ${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/bin/virtualenv_translate.sh

        # Run test suite.
        sudo su ${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/bin/virtualenv_test.sh
    }

    if git_check
    then
       git_pull
       virtualenv_update
    else
        exit 1
    fi

} 2>&1 | tee -a ${TWLIGHT_HOME}/TWLight/logs/update.log
