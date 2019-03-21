FROM library/alpine:latest

ENV PYTHONUNBUFFERED 1
ENV TWLIGHT_HOME=/app

WORKDIR /root/
COPY bin/apk.sh /app/apk.sh
COPY bin/virtualenv_activate.sh /app/bin/virtualenv_activate.sh
COPY bin/virtualenv_migrate.sh /app/bin/virtualenv_migrate.sh
COPY bin/virtualenv_pip_update.sh /app/bin/virtualenv_pip_update.sh
COPY requirements /app/requirements
COPY locale /app/locale

RUN /app/apk.sh

WORKDIR $TWLIGHT_HOME

COPY manage.py /app/manage.py

RUN echo "export PYTHONPATH=\"/usr/lib/python2.7\"; export PYTHONPATH=\"\${PYTHONPATH}:${TWLIGHT_HOME}\"" > /etc/profile.d/pypath.sh && \
    /app/bin/virtualenv_pip_update.sh

COPY TWLight /app/TWLight
COPY local_vars.py /app/TWLight/settings/local_vars.py

EXPOSE 80

CMD ["/root/TWLight/bin/gunicorn", "TWLight.wsgi", "--name", "twlight", "--bind", "0.0.0.0:80", "--workers", "3"]
