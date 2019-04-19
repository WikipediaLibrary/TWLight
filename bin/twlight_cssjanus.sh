#!/usr/bin/env bash
#
# Runs the LTR -> RTL CSS conversion script.

# The production branch should already have updated updated assets from travis.
if [ ! -n "${TWLIGHT_ENV+isset}" ] && [ "${TWLIGHT_ENV}" != "production" ]
then
    # Generate right to left css
    cd ${TWLIGHT_HOME} && node ${TWLIGHT_HOME}/bin/twlight_cssjanus.js || exit 1
fi
