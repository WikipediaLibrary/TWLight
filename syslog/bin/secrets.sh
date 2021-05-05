#!/bin/sh
set -e

if  [ ! -n "${MATOMO_SITEID+isset}" ]
then
    export MATOMO_SITEID=$(cat /run/secrets/MATOMO_SITEID 2>/dev/null)
fi

if  [ ! -n "${MATOMO_AUTH_TOKEN+isset}" ]
then
    export MATOMO_AUTH_TOKEN=$(cat /run/secrets/MATOMO_AUTH_TOKEN 2>/dev/null)
fi
