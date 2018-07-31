#!/usr/bin/env bash

source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh

# update pip dependencies
cd /home/${TWLIGHT_UNIXNAME}
pip install -r ${TWLIGHT_HOME}/requirements/wmf.txt
