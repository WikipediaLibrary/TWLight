FROM library/alpine:latest as twlight_base
# Base dependencies.
RUN apk add --update \
    libjpeg-turbo \
    libxslt-dev \
    mariadb-dev \
    python3;\
    pip3 install virtualenv

FROM twlight_base as twlight_build
# Copy pip requirements.
COPY requirements /requirements

# Build dependencies.
RUN apk add \
    build-base \
    gcc \
    libffi-dev \
    libjpeg-turbo-dev \
    libxml2-dev \
    musl-dev \
    python3-dev \
    zlib-dev ;\
    virtualenv /venv ;\
    source /venv/bin/activate ; \
    pip3 install --upgrade --force pip setuptools ; \
    pip3 install -r /requirements/wmf.txt

FROM twlight_base
COPY --from=twlight_build /venv /venv
ENV PATH="${PATH}:/opt/pandoc-2.7.1/bin" TWLIGHT_HOME=/app PYTHONUNBUFFERED=1 PYTHONPATH="/app:/venv:/usr/lib/python3.8"

# Runtime dependencies.
# Refactoring shell code could remove bash dependency
# mariadb-client Not needed by the running app, but by the backup/restore shell scripts.
# Node stuff for rtl support. This and subsequent node things
# should all be moved out of the running container
# since we just use it to generate a css file.
# CSS Janus is the thing actually used to generate the rtl css.
# Pandoc is used for rendering wikicode resource descriptions
# into html for display. We do need this on the live image.
RUN apk add --update \
    bash \
    gettext \
    git \
    mariadb-client \
    nodejs \
    npm \
    tar ;\
    npm install cssjanus ;\
    wget https://github.com/jgm/pandoc/releases/download/2.7.1/pandoc-2.7.1-linux.tar.gz -P /tmp ;\
    tar -xf /tmp/pandoc-2.7.1-linux.tar.gz --directory /opt

# Utility scripts that run in the virtual environment.
COPY bin /app/bin/

# Bash config
COPY conf/bashrc /root/.bashrc

# i18n.
COPY locale /app/locale

COPY TWLight /app/TWLight

WORKDIR $TWLIGHT_HOME

COPY manage.py /app/manage.py

# Configure static assets.
RUN SECRET_KEY=twlight /app/bin/twlight_static.sh

EXPOSE 80

ENTRYPOINT ["/app/bin/twlight_docker_entrypoint.sh"]
