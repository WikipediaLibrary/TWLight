#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

cd ${TWLIGHT_HOME}

if [ "${1}" = "init" ]
then
    venv_update_cmd="${TWLIGHT_HOME}/bin/./twlight_update.sh"
else
    venv_update_cmd="${TWLIGHT_HOME}/bin/./twlight_update.sh init"
fi

# Pull latest git, apply changes to Django
# If that succeeds, run the test suite
# If that succeeds, restart Green Unicorn

if sudo bash -c "${venv_update_cmd}"; then
    systemctl restart gunicorn || exit 1
else
    exit 1
fi
