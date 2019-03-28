#!/usr/bin/env bash
#
# Runs the LTR -> RTL CSS conversion script.

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
fi
