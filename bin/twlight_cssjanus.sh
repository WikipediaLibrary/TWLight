#!/usr/bin/env bash
#
# Runs the LTR -> RTL CSS conversion script.

# Environment variables should be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    exit 1
fi

# The production branch should already have updated updated assets from travis.
if [ "${TWLIGHT_GIT_REVISION}" != "production" ] && [ "${TWLIGHT_ENV}" != "production" ]
then
    # Generate right to left css
    cd ${TWLIGHT_HOME} && node ${TWLIGHT_HOME}/bin/twlight_cssjanus.js || exit 1
fi
