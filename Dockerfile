FROM library/alpine:latest

ENV PYTHONUNBUFFERED 1
ENV TWLIGHT_HOME=/app

WORKDIR /root/

# System dependencies.
COPY bin/alpine_dependencies.sh /app/alpine_dependencies.sh

# Pip dependencies.
COPY requirements /app/requirements

# Gunicorn shell wrapper.
COPY bin/gunicorn_start.sh /app/bin/gunicorn_start.sh

# Utility scripts.
COPY bin/twlight_backup.sh /app/bin/twlight_backup.sh
COPY bin/twlight_mysqldump.sh /app/bin/twlight_mysqldump.sh
COPY bin/twlight_mysqlimport.sh /app/bin/twlight_mysqlimport.sh
COPY bin/twlight_restore.sh /app/bin/twlight_restore.sh

# Utility scripts that run in the virtual environment.
COPY bin/virtualenv_activate.sh /app/bin/virtualenv_activate.sh
COPY bin/virtualenv_migrate.sh /app/bin/virtualenv_migrate.sh
COPY bin/virtualenv_pip_update.sh /app/bin/virtualenv_pip_update.sh

# i18n.
COPY bin/twlight_cssjanus.js /app/bin/twlight_cssjanus.js
COPY locale /app/locale

RUN /app/alpine_dependencies.sh

WORKDIR $TWLIGHT_HOME

COPY manage.py /app/manage.py

RUN /app/bin/virtualenv_pip_update.sh

COPY TWLight /app/TWLight

EXPOSE 80

CMD ["/app/bin/gunicorn_start.sh"]
