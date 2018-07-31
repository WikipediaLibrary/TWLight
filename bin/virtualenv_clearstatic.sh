#!/usr/bin/env bash

# Generate right to left css
node ${TWLIGHT_HOME}/bin/twlight_cssjanus.js || exit 1

# Load virtual environment
source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh

# Ensure collectedstatic dir exists
mkdir -p ${TWLIGHT_HOME}/TWLight/collectedstatic || exit 1

# Clear and collect css
echo "collectstatic --noinput --clear"
python manage.py collectstatic --noinput --clear || exit 1
