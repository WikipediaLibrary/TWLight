#!/usr/bin/env sh

apk add --update \
    bash \
    build-base \
    gcc \
    jpeg-dev zlib-dev \
    libxml2-dev libxslt-dev \
    musl-dev \
    mariadb-dev \
    python python-dev py-pip \
    py-psycopg2 \

pip install virtualenv
rm -rf /var/cache/apk/*
