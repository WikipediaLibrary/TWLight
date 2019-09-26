#!/usr/bin/env bash
#
# Update Python packages via pip

# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    # update pip dependencies
    cd ~
    pip install -r ${TWLIGHT_HOME}/requirements/wmf.txt
else
    exit 1
fi
