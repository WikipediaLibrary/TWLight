#!/usr/bin/env bash

if  [ ! -n "${DJANGO_DB_NAME+isset}" ]
then
    DJANGO_DB_NAME=$(cat /run/secrets/DJANGO_DB_NAME 2>/dev/null)
    export DJANGO_DB_NAME
fi

if  [ ! -n "${DJANGO_DB_USER+isset}" ]
then
    DJANGO_DB_USER=$(cat /run/secrets/DJANGO_DB_USER 2>/dev/null)
    export DJANGO_DB_USER
fi

if  [ ! -n "${DJANGO_DB_PASSWORD+isset}" ]
then
    DJANGO_DB_PASSWORD=$(cat /run/secrets/DJANGO_DB_PASSWORD 2>/dev/null)
    export DJANGO_DB_PASSWORD
fi

if  [ ! -n "${DKIM_PRIVATE_KEY+isset}" ]
then
    DKIM_PRIVATE_KEY=$(cat /run/secrets/DKIM_PRIVATE_KEY 2>/dev/null)
    export DKIM_PRIVATE_KEY
fi

if  [ ! -n "${SECRET_KEY+isset}" ]
then
    SECRET_KEY=$(cat /run/secrets/SECRET_KEY 2>/dev/null)
    export SECRET_KEY
fi

if  [ ! -n "${TWLIGHT_OAUTH_CONSUMER_KEY+isset}" ]
then
    TWLIGHT_OAUTH_CONSUMER_KEY=$(cat /run/secrets/TWLIGHT_OAUTH_CONSUMER_KEY 2>/dev/null)
    export TWLIGHT_OAUTH_CONSUMER_KEY
fi

if  [ ! -n "${TWLIGHT_OAUTH_CONSUMER_SECRET+isset}" ]
then
    TWLIGHT_OAUTH_CONSUMER_SECRET=$(cat /run/secrets/TWLIGHT_OAUTH_CONSUMER_SECRET 2>/dev/null)
    export TWLIGHT_OAUTH_CONSUMER_SECRET
fi

if  [ ! -n "${TWLIGHT_EZPROXY_SECRET+isset}" ]
then
    TWLIGHT_EZPROXY_SECRET=$(cat /run/secrets/TWLIGHT_EZPROXY_SECRET 2>/dev/null)
    export TWLIGHT_EZPROXY_SECRET
fi

if  [ ! -n "${MW_API_EMAIL_USER+isset}" ]
then
    MW_API_EMAIL_USER=$(cat /run/secrets/MW_API_EMAIL_USER 2>/dev/null)
    export MW_API_EMAIL_USER
fi
if  [ ! -n "${MW_API_EMAIL_PASSWORD+isset}" ]
then
    MW_API_EMAIL_PASSWORD=$(cat /run/secrets/MW_API_EMAIL_PASSWORD 2>/dev/null)
    export MW_API_EMAIL_PASSWORD
fi
