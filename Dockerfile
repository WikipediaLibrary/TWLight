FROM library/alpine:latest

ENV PATH="${PATH}:/opt/pandoc-2.7.1/bin"
ENV TWLIGHT_HOME=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="${PYTHONPATH}:/usr/lib/python2.7:${TWLIGHT_HOME}"

WORKDIR /root/

# System dependencies.
RUN apk add --update \
    bash \
    build-base \
    gcc \
    jpeg-dev zlib-dev \
    libxml2-dev libxslt-dev \
    musl-dev \
    mariadb-client \
    mariadb-dev \
    nodejs \
    npm \
    python python-dev py-pip \
    py-psycopg2 \
    tar ;\
    # Node.js setup.
    npm install cssjanus ; \
    # Python setup.
    pip install virtualenv ; \
    # Pandoc is used for rendering wikicode resource descriptions into html for display.
    wget https://github.com/jgm/pandoc/releases/download/2.7.1/pandoc-2.7.1-linux.tar.gz -P /tmp ; \
    tar -xf /tmp/pandoc-2.7.1-linux.tar.gz --directory /opt

# Pip dependencies.
COPY requirements /app/requirements

# Utility scripts that run in the virtual environment.
COPY bin/virtualenv_*.sh /app/bin/

# Other utility scripts.
COPY bin/twlight_*.sh /app/bin/

# i18n.
COPY bin/twlight_cssjanus.js /app/bin/twlight_cssjanus.js
COPY locale /app/locale

WORKDIR $TWLIGHT_HOME

COPY manage.py /app/manage.py
RUN /app/bin/virtualenv_pip_update.sh
EXPOSE 80
