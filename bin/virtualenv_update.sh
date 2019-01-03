#!/usr/bin/env bash
set -eo pipefail

if [ "${USER}" != "root" ]
then
    echo "twlight_update.sh must be run as root!"
    exit 1
fi

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# Verify that the unix user can talk to the remote.
cd ${TWLIGHT_HOME}
if git fetch --dry-run
then
    # Fetch latest code from ${TWLIGHT_GIT_REVISION}.
    git checkout .
    git pull origin ${TWLIGHT_GIT_REVISION}

    # Make sure ${TWLIGHT_UNIXNAME} owns the .git tree
    chown -R ${TWLIGHT_UNIXNAME}:${TWLIGHT_UNIXNAME} ${TWLIGHT_HOME}/.git
else
    exit 1
fi

# Update pip dependencies.
sudo su ${TWLIGHT_UNIXNAME} bash ${TWLIGHT_HOME}/bin/virtualenv_pip_update.sh

# Process static assets.
sudo su ${TWLIGHT_UNIXNAME} bash ${TWLIGHT_HOME}/bin/virtualenv_clearstatic.sh

# Run migrations.
sudo su ${TWLIGHT_UNIXNAME} bash ${TWLIGHT_HOME}/bin/virtualenv_migrate.sh

# Compile translations.
sudo su ${TWLIGHT_UNIXNAME} bash ${TWLIGHT_HOME}/bin/virtualenv_translate.sh
