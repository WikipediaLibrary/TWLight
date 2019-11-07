#!/usr/bin/env bash

# Activates the Django virtual environment

# Environment variables should be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    exit 1
fi

# Get secrets.
if  [ ! -n "${SECRET_KEY+isset}" ]
then
    source /app/bin/twlight_docker_secrets.sh
fi

# Virtualenv scripts need to be run as www
if [ "${USER}" != "${TWLIGHT_UNIXNAME}" ]
then
    echo "virtualenv must be run as ${TWLIGHT_UNIXNAME}, but was run as ${USER}: Try \"sudo su ${TWLIGHT_UNIXNAME}\""
    return 1
fi

# Check to see if we're in a virtualenv or not.
# Cribbed from: https://stackoverflow.com/a/15454916
ACTIVATED=$(python3 -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')
if [ "${ACTIVATED}" -eq 0 ]
then

    # Activate Django virtualenv.
    source /venv/bin/activate
fi

# Move to the project root.
cd $TWLIGHT_HOME

