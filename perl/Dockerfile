FROM quay.io/wikipedialibrary/debian:buster-slim as perl_build
ENV PERL_VERSION=5.32.1
# Base dependencies; split out to create cachable layer.
RUN apt update; \
    apt install -y \
    build-essential \
    gcc \
    wget ; \
    apt clean ; \
    wget https://www.cpan.org/src/5.0/perl-${PERL_VERSION}.tar.gz ; \
    tar -xvf perl-${PERL_VERSION}.tar.gz ; \
    cd perl-${PERL_VERSION} ; \
    ./Configure -des -Dprefix=/opt/perl ; \
    make && make test && make install

FROM quay.io/wikipedialibrary/debian:buster-slim
COPY --from=perl_build /opt/perl /opt/perl

ENTRYPOINT ["/opt/perl/bin/perl"]
