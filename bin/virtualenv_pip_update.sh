#!/usr/bin/env bash
#
# Update Python packages via pip

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    # update pip dependencies
    cd /home/${TWLIGHT_UNIXNAME}
    pip install -r ${TWLIGHT_HOME}/requirements/wmf.txt
else
    exit 1
fi
