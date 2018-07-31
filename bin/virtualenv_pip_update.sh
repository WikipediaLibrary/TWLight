#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh

# update pip dependencies
cd /home/${TWLIGHT_UNIXNAME}
pip install -r ${TWLIGHT_HOME}/requirements/wmf.txt
