#!/usr/bin/env sh

source /srv/syslog/bin/secrets.sh

while IFS= read -r line; do
  if  [ -n "${MATOMO_FQDN+isset}" ] && [ -n "${MATOMO_AUTH_TOKEN+isset}" ] && [ -n "${MATOMO_SITEID+isset}" ]
  then
    echo ${line} | /srv/syslog/bin/import_logs.py \
    --url=https://${MATOMO_FQDN}/ --token-auth=${MATOMO_AUTH_TOKEN} \
    --idsite=${MATOMO_SITEID} --recorders=4 \
    --enable-http-errors \
    --enable-http-redirects \
    --log-format-name=nginx_json -
  fi
done
