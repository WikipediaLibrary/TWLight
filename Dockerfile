FROM twlight_base

ENV PATH="${PATH}:/opt/pandoc-2.7.1/bin" TWLIGHT_HOME=/app PYTHONUNBUFFERED=1 PYTHONPATH="${PYTHONPATH}:/usr/lib/python2.7:${TWLIGHT_HOME}"

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

# i18n.
COPY locale /app/locale

COPY TWLight /app/TWLight

WORKDIR $TWLIGHT_HOME

COPY manage.py /app/manage.py

EXPOSE 80

ENTRYPOINT ["/bin/bash", "-c", "source /app/bin/virtualenv_activate.sh && /venv/bin/gunicorn TWLight.wsgi"]
