#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

venv_update_cmd="${TWLIGHT_HOME}/bin/./virtualenv_update.sh >>${TWLIGHT_HOME}/TWLight/logs/update.log 2>&1"
venv_test_cmd="${TWLIGHT_HOME}/bin/./virtualenv_test.sh >>${TWLIGHT_HOME}/TWLight/logs/test.log 2>&1"

# Make sure ${TWLIGHT_UNIXNAME} owns the .git tree
chown -R ${TWLIGHT_UNIXNAME}:${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/.git

# Pull latest git, apply changes to Django
# If that succeeds, run the test suite
# If that succeeds, restart Green Unicorn

if sudo su ${TWLIGHT_UNIXNAME} bash -c "${venv_update_cmd}"; then
    if sudo su ${TWLIGHT_UNIXNAME} bash -c "${venv_test_cmd}"; then
        systemctl restart gunicorn || exit 1
    else
        exit 1
    fi
else
    exit 1
fi
