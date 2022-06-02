FROM quay.io/wikipedialibrary/python:3.7-slim-buster-updated as twlight_base
# Base dependencies.
RUN apt update ; \
    apt install -y --no-install-recommends \
    libmariadbclient-dev ; \
    ln -s /usr/bin/mariadb_config /usr/bin/mysql_config ; \
    rm -rf /var/lib/apt/lists/*; \
    pip3 install virtualenv

FROM twlight_base as twlight_build
# Copy pip requirements.
ARG REQUIREMENTS_FILE=wmf.txt
ENV REQUIREMENTS_FILE=${REQUIREMENTS_FILE}
COPY requirements /requirements

# Build dependencies.
RUN apt update ; \
    apt install -y --no-install-recommends \
    gcc \
    python3-dev ; \
    rm -rf /var/lib/apt/lists/*; \
    virtualenv /venv ; \
    . /venv/bin/activate ; \
    pip3 install -r /requirements/${REQUIREMENTS_FILE}

FROM twlight_base
COPY --from=twlight_build /venv /venv
COPY --from=quay.io/wikipedialibrary/debian_perl:latest /opt/perl /opt/perl
ENV PATH="/opt/perl/bin:${PATH}" TWLIGHT_HOME=/app PYTHONUNBUFFERED=1 PYTHONPATH="/app:/venv"

# Runtime dependencies.
# Refactoring shell code could remove bash dependency
# mariadb-client Not needed by the running app, but by the backup/restore shell scripts.
# Node stuff for rtl support. This and subsequent node things
# should all be moved out of the running container
# since we just use it to generate a css file.
# CSS Janus is the thing actually used to generate the rtl css.
RUN apt update ; \
    apt install -y --no-install-recommends \
    bash \
    gettext \
    git \
    mariadb-client \
    nodejs \
    npm \
    tar \
    wget ; \
    rm -rf /var/lib/apt/lists/*; \
    /usr/bin/npm install cssjanus

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
