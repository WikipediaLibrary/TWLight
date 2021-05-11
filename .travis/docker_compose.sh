#!/usr/bin/env bash
export DOCKER_BUILDKIT=1 # enable buildkit for parallel builds
export COMPOSE_DOCKER_CLI_BUILD=1 # use docker cli for building

docker-compose build twlight_base
docker tag "quay.io/wikipedialibrary/twlight_base:local" "quay.io/wikipedialibrary/twlight_base:${BRANCH_TAG}"
docker tag "quay.io/wikipedialibrary/twlight_base:local" "quay.io/wikipedialibrary/twlight_base:${BUILD_TAG}"
docker tag "quay.io/wikipedialibrary/twlight_base:local" "quay.io/wikipedialibrary/twlight_base:${COMMIT_TAG}"
docker-compose build twlight_build
docker tag "quay.io/wikipedialibrary/twlight_build:local" "quay.io/wikipedialibrary/twlight_build:${BRANCH_TAG}"
docker tag "quay.io/wikipedialibrary/twlight_build:local" "quay.io/wikipedialibrary/twlight_build:${BUILD_TAG}"
docker tag "quay.io/wikipedialibrary/twlight_build:local" "quay.io/wikipedialibrary/twlight_build:${COMMIT_TAG}"
docker-compose build twlight
docker tag "quay.io/wikipedialibrary/twlight:local" "quay.io/wikipedialibrary/twlight:${BRANCH_TAG}"
docker tag "quay.io/wikipedialibrary/twlight:local" "quay.io/wikipedialibrary/twlight:${BUILD_TAG}"
docker tag "quay.io/wikipedialibrary/twlight:local" "quay.io/wikipedialibrary/twlight:${COMMIT_TAG}"
docker-compose build syslog
docker tag "quay.io/wikipedialibrary/twlight_syslog:local" "quay.io/wikipedialibrary/twlight_syslog:${BRANCH_TAG}"
docker tag "quay.io/wikipedialibrary/twlight_syslog:local" "quay.io/wikipedialibrary/twlight_syslog:${BUILD_TAG}"
docker tag "quay.io/wikipedialibrary/twlight_syslog:local" "quay.io/wikipedialibrary/twlight_syslog:${COMMIT_TAG}"

docker-compose up -d db twlight
