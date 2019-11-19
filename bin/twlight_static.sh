#!/usr/bin/env bash
#
# Runs the LTR -> RTL CSS conversion script and collects static files.

# Generate right to left css
cd ${TWLIGHT_HOME} && node ${TWLIGHT_HOME}/bin/twlight_cssjanus.js || exit 1
# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    # Ensure collectedstatic dir exists
    mkdir -p ${TWLIGHT_HOME}/TWLight/collectedstatic || exit 1

    # Clear and collect css
    echo "collectstatic --noinput --clear"
    python3 manage.py collectstatic --noinput --clear || exit 1
else
    exit 1
fi
