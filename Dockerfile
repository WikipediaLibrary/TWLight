FROM quay.io/wikipedialibrary/debian:buster-slim as twlight_base
# Base dependencies.
RUN apt update; \
    apt install -y \
    libjpeg62-turbo \
    libxslt1-dev \
    libmariadb-dev \
    python3 \
    python3-pip ; \
    pip3 install virtualenv

FROM twlight_base as twlight_build
# Copy pip requirements.
COPY requirements /requirements

# Build dependencies.
RUN apt install -y \
    build-essential \
    gcc \
    libffi-dev \
    libjpeg62-turbo-dev \
    libxml2-dev \
    musl-dev \
    python3-dev \
    zlib1g-dev ; \
    virtualenv /venv ; \
    . /venv/bin/activate ; \
    pip3 install -r /requirements/wmf.txt

FROM twlight_base
COPY --from=twlight_build /venv /venv
COPY --from=quay.io/wikipedialibrary/debian_perl:latest /opt/perl /opt/perl
ENV PATH="/opt/perl/bin:${PATH}" TWLIGHT_HOME=/app PYTHONUNBUFFERED=1 PYTHONPATH="/app:/venv:/usr/lib/python3.8"

# Runtime dependencies.
# Refactoring shell code could remove bash dependency
# mariadb-client Not needed by the running app, but by the backup/restore shell scripts.
# Node stuff for rtl support. This and subsequent node things
# should all be moved out of the running container
# since we just use it to generate a css file.
# CSS Janus is the thing actually used to generate the rtl css.
# Pandoc is used for rendering wikicode resource descriptions
# into html for display. We do need this on the live image.
RUN apt install -y \
    bash \
    gettext \
    git \
    mariadb-client \
    nodejs \
    npm \
    pandoc \
    tar \
    wget ; \
    apt clean ; \
    npm install cssjanus

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
