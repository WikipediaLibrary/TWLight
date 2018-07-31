#!/usr/bin/env bash

source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh

echo "test --noinput"
python manage.py test --noinput
