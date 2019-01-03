#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

if [ "${1}" = "init" ]
then
     init="true"
fi

cd ${TWLIGHT_HOME}
update() {
    venv_update_cmd="${TWLIGHT_HOME}/bin/./twlight_update.sh"
    venv_test_cmd="${TWLIGHT_HOME}/bin/./virtualenv_test.sh"

    # Make sure ${TWLIGHT_UNIXNAME} owns the .git tree
    chown -R ${TWLIGHT_UNIXNAME}:${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/.git

    # Pull latest git, apply changes to Django
    # If that succeeds, run the test suite
    # If that succeeds, restart Green Unicorn

    if bash -c "${venv_update_cmd}"; then
        if sudo su ${TWLIGHT_UNIXNAME} bash -c "${venv_test_cmd}"; then
            systemctl restart gunicorn || exit 1
        else
            exit 1
        fi
    else
        exit 1
    fi
}

if [ "${init}" = "true" ]
then
    echo "Init"
    update
else
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
    elif [ "${local}" = "${base}" ]
    then
        echo "Need to pull"
        update
    elif [ "${remote}" = "${base}" ]
    then
        echo "Need to push"
        exit 1
    else
        echo "Diverged"
        exit 1
    fi
fi
