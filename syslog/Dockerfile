FROM quay.io/wikipedialibrary/alpine:3.11-updated
RUN apk add --update \
  python3 \
  syslog-ng \
  ; \
  mkdir -p /srv/syslog;

COPY bin /srv/syslog/bin
COPY conf/ /etc/syslog-ng/conf.d/
ENTRYPOINT ["/srv/syslog/bin/entrypoint.sh"]
