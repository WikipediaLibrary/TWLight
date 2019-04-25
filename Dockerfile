FROM library/alpine:latest as twlight_base
RUN apk add --update \
    libjpeg-turbo \
    mariadb-dev \
    # Python, duh.
    python py-pip ;\
    pip install virtualenv

FROM twlight_base as twlight_build
# Build dependencies.
RUN apk add --update \
    build-base \
    gcc \
    libjpeg-turbo-dev \
    libxml2-dev libxslt-dev \
    musl-dev \
    python-dev \
    zlib-dev

# Pip dependencies.
COPY requirements /requirements
RUN virtualenv /venv ;\
    source /venv/bin/activate ;\
    pip install -r /requirements/wmf.txt

FROM twlight_base
COPY --from=twlight_build /venv /venv
ENV PATH="${PATH}:/opt/pandoc-2.7.1/bin" TWLIGHT_HOME=/app PYTHONUNBUFFERED=1 PYTHONPATH="/app:/usr/lib/python2.7"

RUN apk add --update \
    # Refactoring shell code could remove this dependency
    bash \
    # Not needed by the running app, but by the backup/restore shell scripts.
    mariadb-client \
    # Node stuff for rtl support. This and subsequent node things
    # should all be moved out of the running container
    # since we just use it to generate a css file.
    nodejs \
    npm \
    tar ;\
    # CSS Janus is the thing actually used to generate the rtl css.
    npm install cssjanus ;\
    # Pandoc is used for rendering wikicode resource descriptions
    # into html for display. We do need this on the live image.
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

# Create RTL Stylesheet
RUN source /app/bin/virtualenv_activate.sh ;\
    /app/bin/twlight_cssjanus.sh

EXPOSE 80

ENTRYPOINT ["/app/bin/twlight_docker_entrypoint.sh"]
