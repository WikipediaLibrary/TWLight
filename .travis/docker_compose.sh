#!/usr/bin/env bash
export DOCKER_BUILDKIT=1 # enable buildkit for parallel builds
export COMPOSE_DOCKER_CLI_BUILD=1 # use docker cli for building

docker-compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.travis.yml build --quiet twlight syslog
docker tag "quay.io/wikipedialibrary/twlight:local" "quay.io/wikipedialibrary/twlight:${BRANCH_TAG}"
docker tag "quay.io/wikipedialibrary/twlight:local" "quay.io/wikipedialibrary/twlight:${BUILD_TAG}"
docker tag "quay.io/wikipedialibrary/twlight:local" "quay.io/wikipedialibrary/twlight:${COMMIT_TAG}"
docker tag "quay.io/wikipedialibrary/twlight_syslog:local" "quay.io/wikipedialibrary/twlight_syslog:${BRANCH_TAG}"
docker tag "quay.io/wikipedialibrary/twlight_syslog:local" "quay.io/wikipedialibrary/twlight_syslog:${BUILD_TAG}"
docker tag "quay.io/wikipedialibrary/twlight_syslog:local" "quay.io/wikipedialibrary/twlight_syslog:${COMMIT_TAG}"

docker-compose up -d db twlight
