#!/usr/bin/env bash

# Fetch latest code from ${TWLIGHT_GIT_REVISION}.
cd ${TWLIGHT_HOME}
git checkout .
git pull origin ${TWLIGHT_GIT_REVISION}

# Update pip dependencies.
bash ${TWLIGHT_HOME}/bin/virtualenv_pip_update.sh || exit 1

# Run migrations.
bash ${TWLIGHT_HOME}/bin/virtualenv_migrate.sh || exit 1

# Compile translations.
bash ${TWLIGHT_HOME}/bin/virtualenv_translate.sh || exit 1

# Process static assets.
bash ${TWLIGHT_HOME}/bin/virtualenv_clearstatic.sh || exit 1
