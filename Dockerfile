FROM quay.io/wikipedialibrary/python:3.11-slim-trixie-updated
ARG EXPIRES=never
LABEL quay.expires-after=${EXPIRES}
ARG REQUIREMENTS_FILE=wmf.txt
ENV REQUIREMENTS_FILE=${REQUIREMENTS_FILE} \
    TWLIGHT_HOME=/app \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/perl/bin:${PATH}"

# Build + runtime dependencies. gcc / libmariadb-dev / libmariadb-dev-compat
# are pulled in only for mysqlclient's C-extension build and dropped after
# install; mysqlclient links libmariadb3 at runtime, a separate package
# pulled in as a dependency. The python headers come from the base image,
# not Debian. mariadb-client is runtime for the backup/restore scripts.
COPY requirements /requirements
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libmariadb-dev \
        libmariadb-dev-compat \
        bash \
        gettext \
        git \
        mariadb-client \
        tar \
        gcc \
    && python -m pip install --no-cache-dir --upgrade setuptools wheel pip \
    && pip install --no-cache-dir -r /requirements/${REQUIREMENTS_FILE} \
    && apt-get purge -y gcc libmariadb-dev libmariadb-dev-compat \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY --from=quay.io/wikipedialibrary/debian_perl:latest /opt/perl /opt/perl

WORKDIR ${TWLIGHT_HOME}

COPY bin /app/bin/
COPY conf/bashrc /root/.bashrc
COPY conf/client.cnf /etc/mysql/conf.d/client.cnf
COPY locale /app/locale
COPY twlight_cssjanus /app/twlight_cssjanus

# nodejs stays at runtime: bin/static.sh runs `node twlight_cssjanus` for
# the LTR->RTL CSS generation, both here and if static.sh is ever re-run
# after the image is built. npm is build-only (it just fetches cssjanus's
# own deps), so install and purge it in this one layer -- purging in a
# later layer wouldn't shrink anything, since Docker layers are
# append-only and a later delete can't reclaim an earlier layer's bytes.
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && cd /app/twlight_cssjanus && npm install \
    && apt-get purge -y npm \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY TWLight /app/TWLight
COPY manage.py /app/manage.py

# Configure static assets. TWLIGHT_ENV is required now that manage.py refuses
# to guess a settings module; production is what the build used implicitly
# before, so collectstatic output stays identical.
RUN SECRET_KEY=twlight TWLIGHT_ENV=production /app/bin/static.sh

EXPOSE 80
