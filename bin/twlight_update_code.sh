#!/usr/bin/env bash
set -eo pipefail

# Use a lockfile to prevent overruns.
self=$(basename ${0})
exec {lockfile}>/var/lock/${self}
flock -n ${lockfile}
{

    {

        # print the date for logging purposes
        echo [$(date)]

        # init is basically a --force flag.
        if [ "${1}" = "init" ]
        then
             init="true"
        fi

        git_check() {
            # Verify that the unix user can talk to the remote.
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
                docker-compose exec twlight bin/twlight_backup.sh
            fi

            # Pull latest code.
            git pull
        }

        virtualenv_update() {

            # Run migrations.
            docker exec -it $(docker ps -q  -f name=twlight_stack_twlight) bin/virtualenv_migrate.sh

            # Compile translations.
            docker exec -it $(docker ps -q  -f name=twlight_stack_twlight) bin/virtualenv_translate.sh

            # Run test suite.
            docker exec -it $(docker ps -q  -f name=twlight_stack_twlight) /bin/virtualenv_test.sh
        }

        # Verify that we can pull.
        if git_check
        then
            # Pull.
            git_pull
            # Update virtual environment and run django managment commands.
            virtualenv_update
            # Rebuild to pick up changes.
            docker-compose -f docker-compose.yml -f docker-compose.${TWLIGHT_ENV}.yml build  && \
            docker stack deploy -c docker-compose.yml -c docker-compose.${TWLIGHT_ENV}.yml twlight_stack
        else
            exit 1
        fi

    } 2>&1
} {lockfile}>&-
