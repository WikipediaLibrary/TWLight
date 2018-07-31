#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# Start in TWLight user's home dir.
cd /home/${TWLIGHT_UNIXNAME}

# Suppress a non-useful warning message that occurs when gunicorn is running.
virtualenv TWLight 2>/dev/null

# Activate Django virtualenv.
source TWLight/bin/activate

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# Move to the project root.
cd $TWLIGHT_HOME
