#!/usr/bin/env bash

# Start in TWLight user's home dir.
cd ~

# Suppress a non-useful warning message that occurs when gunicorn is running.
virtualenv TWLight 2>/dev/null

# Activate Django virtualenv.
source TWLight/bin/activate

# Grab TWLight global environment variables.
source /etc/profile.d/twlight_global_env.sh

# Move to the project root.
cd $TWLIGHT_HOME
