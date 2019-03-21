#!/usr/bin/env sh

# Packaged dependencies.
apk add --update \
    bash \
    build-base \
    gcc \
    jpeg-dev zlib-dev \
    libxml2-dev libxslt-dev \
    musl-dev \
    mariadb-client \
    mariadb-dev \
    python python-dev py-pip \
    py-psycopg2 \
    tar \

# Python setup.
pip install virtualenv
rm -rf /var/cache/apk/*
echo "export PYTHONPATH=\"/usr/lib/python2.7\"; export PYTHONPATH=\"\${PYTHONPATH}:${TWLIGHT_HOME}\"" > /etc/profile.d/pypath.sh

# Pandoc is used for rendering wikicode resource descriptions into html for display.
wget https://github.com/jgm/pandoc/releases/download/2.7.1/pandoc-2.7.1-linux.tar.gz -P /tmp
tar -xf /tmp/pandoc-2.7.1-linux.tar.gz --directory /opt
echo "export PATH=\"\${PATH}:/opt/pandoc-2.7.1/bin\"" > /etc/profile.d/pandocpath.sh


echo "
. /etc/profile
" >> /root/.profile
