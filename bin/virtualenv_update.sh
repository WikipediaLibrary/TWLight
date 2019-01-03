#!/usr/bin/env bash
set -eo pipefail

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# Verify that the unix user has proper group membership.
if groups | grep &>/dev/null "\b${TWLIGHT_UNIXNAME}\b"
then
    # Verify that the unix user can talk to the remote.
    if git fetch --dry-run
    then
        # Fetch latest code from ${TWLIGHT_GIT_REVISION}.
        cd ${TWLIGHT_HOME}
        git checkout .
        git pull origin ${TWLIGHT_GIT_REVISION}
    else
        exit 1
    fi
else
    echo "git pull must be run as member of ${TWLIGHT_UNIXNAME} group!"
    exit 1
fi

# Update pip dependencies.
bash ${TWLIGHT_HOME}/bin/virtualenv_pip_update.sh

# Process static assets.
bash ${TWLIGHT_HOME}/bin/virtualenv_clearstatic.sh

# Run migrations.
bash ${TWLIGHT_HOME}/bin/virtualenv_migrate.sh

# Compile translations.
bash ${TWLIGHT_HOME}/bin/virtualenv_translate.sh
