#!/usr/bin/env bash
#
# Update Python packages via pip

# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    # update pip3 dependencies
    cd ~
    pip3 install -r ${TWLIGHT_HOME}/requirements/wmf.txt
else
    exit 1
fi
