#!/usr/bin/env bash
#
# Runs the Django collectstatic process (https://docs.djangoproject.com/en/1.11/ref/contrib/staticfiles/)

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# The production branch should already have updated updated assets from travis.
if [ "${TWLIGHT_GIT_REVISION}" != "production" ] && [ "${TWLIGHT_ENV}" != "production" ]
then
    # Generate right to left css
    cd ${TWLIGHT_HOME} && node ${TWLIGHT_HOME}/bin/twlight_cssjanus.js || exit 1

    # Load virtual environment
    source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh

    # Ensure collectedstatic dir exists
    mkdir -p ${TWLIGHT_HOME}/TWLight/collectedstatic || exit 1

    # Clear and collect css
    echo "collectstatic --noinput --clear"
    python manage.py collectstatic --noinput --clear || exit 1
fi
