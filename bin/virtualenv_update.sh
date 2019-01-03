#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# Load virtual environment to leverage the common sanity checks, not because we need python (we don't).
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    # Fetch latest code from ${TWLIGHT_GIT_REVISION}.
    cd ${TWLIGHT_HOME}
    git checkout .
    git pull origin ${TWLIGHT_GIT_REVISION}
else
    exit 1
fi

# Update pip dependencies.
bash ${TWLIGHT_HOME}/bin/virtualenv_pip_update.sh || exit 1

# Process static assets.
bash ${TWLIGHT_HOME}/bin/virtualenv_clearstatic.sh || exit 1

# Run migrations.
bash ${TWLIGHT_HOME}/bin/virtualenv_migrate.sh || exit 1

# Compile translations.
bash ${TWLIGHT_HOME}/bin/virtualenv_translate.sh || exit 1
