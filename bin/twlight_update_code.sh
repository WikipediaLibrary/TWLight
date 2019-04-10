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

    {

        # print the date for logging purposes
        echo [$(date)]

        # Must run as root.
        # $USER env may not be set if run from puppet, so we check with whoami.
        user=$(whoami)
        if [ "${user}" != "root" ]
        then
            echo "twlight_update_code.sh must be run as root; was run as ${user}!"
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

                if [ "${init}" = "true" ]
                then
                    echo "Forced to pull"
                    return 0
                elif [ "${local}" = "${remote}" ]
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
            git pull

            # Make sure ${TWLIGHT_UNIXNAME} owns everything.
            chown -R ${TWLIGHT_UNIXNAME}:${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}
        }

        virtualenv_update() {
            # Update pip dependencies.
            sudo su ${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/bin/virtualenv_pip_update.sh

            # Generate RTL CSS.
            sudo su ${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/bin/twlight_cssjanus.sh

            # Run migrations.
            sudo su ${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/bin/virtualenv_migrate.sh

            # Compile translations.
            sudo su ${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/bin/virtualenv_translate.sh

            # Run test suite.
            sudo su ${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/bin/virtualenv_test.sh
        }

        # Verify that we can pull.
        if git_check
        then
            # Pull.
            git_pull
            # Update virtual environment and run django managment commands.
            virtualenv_update
            # Restart services to pick up changes.
            systemctl restart gunicorn
        else
            exit 1
        fi

    } 2>&1
} {lockfile}>&-
