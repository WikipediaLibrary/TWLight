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
