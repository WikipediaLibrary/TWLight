FROM quay.io/wikipedialibrary/python:3.11-slim-trixie-updated
ARG EXPIRES=never
LABEL quay.expires-after=${EXPIRES}
ARG REQUIREMENTS_FILE=wmf.txt
ENV REQUIREMENTS_FILE=${REQUIREMENTS_FILE} \
    TWLIGHT_HOME=/app \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/perl/bin:${PATH}"

# Build + runtime dependencies. gcc is pulled in for pip's C-extension
# builds and dropped after install; the python headers come from the base
# image, not Debian. mariadb-client is runtime for the backup/restore
# scripts; node/npm are runtime for the LTR->RTL CSS generation done at
# collectstatic time.
COPY requirements /requirements
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libmariadb-dev \
        libmariadb-dev-compat \
        bash \
        gettext \
        git \
        mariadb-client \
        nodejs \
        npm \
        tar \
        wget \
        gcc \
    && python -m pip install --no-cache-dir --upgrade setuptools wheel pip \
    && pip install --no-cache-dir -r /requirements/${REQUIREMENTS_FILE} \
    && apt-get purge -y gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY --from=quay.io/wikipedialibrary/debian_perl:latest /opt/perl /opt/perl

WORKDIR ${TWLIGHT_HOME}

COPY bin /app/bin/
COPY conf/bashrc /root/.bashrc
COPY conf/client.cnf /etc/mysql/conf.d/client.cnf
COPY locale /app/locale
COPY TWLight /app/TWLight
COPY twlight_cssjanus /app/twlight_cssjanus
RUN cd /app/twlight_cssjanus/ && npm install
COPY manage.py /app/manage.py

# Configure static assets. TWLIGHT_ENV is required now that manage.py refuses
# to guess a settings module; production is what the build used implicitly
# before, so collectstatic output stays identical.
RUN SECRET_KEY=twlight TWLIGHT_ENV=production /app/bin/static.sh

EXPOSE 80
