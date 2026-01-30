FROM quay.io/wikipedialibrary/python:3.11-slim-bullseye-updated AS twlight_base
ARG EXPIRES=never
LABEL quay.expires-after=${EXPIRES}
# Base dependencies.
RUN apt update ; \
    apt install -y --no-install-recommends \
    libmariadb-dev \
    libmariadb-dev-compat; \
    rm -rf /var/lib/apt/lists/*; \
    python -m pip install --upgrade setuptools wheel pip; \
    pip3 install virtualenv

FROM twlight_base AS twlight_build
# Copy pip requirements.
ARG REQUIREMENTS_FILE=wmf.txt
ENV REQUIREMENTS_FILE=${REQUIREMENTS_FILE}
COPY requirements /requirements

# Build dependencies.
RUN apt update ; \
    apt install -y --no-install-recommends \
    gcc \
    git \
    python3-dev ; \
    rm -rf /var/lib/apt/lists/*; \
    virtualenv /venv ; \
    . /venv/bin/activate ; \
    pip3 install -r /requirements/${REQUIREMENTS_FILE}

FROM twlight_base
COPY --from=twlight_build /venv /venv
COPY --from=quay.io/wikipedialibrary/debian_perl:latest /opt/perl /opt/perl
ENV PATH="/venv/bin:/opt/perl/bin:${PATH}" TWLIGHT_HOME=/app PYTHONUNBUFFERED=1 PYTHONPATH="/app:/venv/lib/python3.11/site-packages"
WORKDIR ${TWLIGHT_HOME}
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
    rm -rf /var/lib/apt/lists/*;


# Utility scripts that run in the virtual environment.
COPY bin /app/bin/

# Bash config
COPY conf/bashrc /root/.bashrc

# i18n.
COPY locale /app/locale

COPY TWLight /app/TWLight

COPY twlight_cssjanus /app/twlight_cssjanus
RUN cd /app/twlight_cssjanus/ && npm install

WORKDIR $TWLIGHT_HOME

COPY manage.py /app/manage.py

# Configure static assets.
RUN SECRET_KEY=twlight /app/bin/twlight_static.sh

EXPOSE 80

ENTRYPOINT ["/app/bin/virtualenv_activate.sh"]
