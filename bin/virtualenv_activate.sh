#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

if [ "${USER}" != "${TWLIGHT_UNIXNAME}" ]
then
    echo "virtualenv must be run as ${TWLIGHT_UNIXNAME}; was run as ${USER}!"
    return 1
fi

# Check to see if we're in a virtualenv or not.
# Cribbed from: https://stackoverflow.com/a/15454916
ACTIVATED=$(python -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')
if [ "${ACTIVATED}" -eq 0 ]
then
    # Start in TWLight user's home dir.
    cd /home/${TWLIGHT_UNIXNAME}

    # Suppress a non-useful warning message that occurs when gunicorn is running.
    virtualenv TWLight 2>/dev/null

    # Activate Django virtualenv.
    source TWLight/bin/activate
fi

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# Move to the project root.
cd $TWLIGHT_HOME
