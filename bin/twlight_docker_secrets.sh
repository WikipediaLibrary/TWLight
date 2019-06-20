#!/usr/bin/env bash

if  [ ! -n "${DJANGO_DB_NAME+isset}" ]
then
    export DJANGO_DB_NAME=$(cat /run/secrets/DJANGO_DB_NAME 2>/dev/null)
fi

if  [ ! -n "${DJANGO_DB_USER+isset}" ]
then
    export DJANGO_DB_USER=$(cat /run/secrets/DJANGO_DB_USER 2>/dev/null)
fi

if  [ ! -n "${DJANGO_DB_PASSWORD+isset}" ]
then
    export DJANGO_DB_PASSWORD=$(cat /run/secrets/DJANGO_DB_PASSWORD 2>/dev/null)
fi

if  [ ! -n "${SECRET_KEY+isset}" ]
then
    export SECRET_KEY=$(cat /run/secrets/SECRET_KEY 2>/dev/null)
fi

if  [ ! -n "${TWLIGHT_OAUTH_CONSUMER_KEY+isset}" ]
then
    export TWLIGHT_OAUTH_CONSUMER_KEY=$(cat /run/secrets/TWLIGHT_OAUTH_CONSUMER_KEY 2>/dev/null)
fi

if  [ ! -n "${TWLIGHT_OAUTH_CONSUMER_SECRET+isset}" ]
then
    export TWLIGHT_OAUTH_CONSUMER_SECRET=$(cat /run/secrets/TWLIGHT_OAUTH_CONSUMER_SECRET 2>/dev/null)
fi

if  [ ! -n "${TWLIGHT_EZPROXY_SECRET+isset}" ]
then
    export TWLIGHT_EZPROXY_SECRET=$(cat /run/secrets/TWLIGHT_EZPROXY_SECRET 2>/dev/null)
fi
