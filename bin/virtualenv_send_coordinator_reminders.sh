#!/usr/bin/env bash

source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh

python manage.py send_coordinator_reminders --app_status PENDING
