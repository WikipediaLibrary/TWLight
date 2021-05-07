#!/usr/bin/env bash
export DOCKER_BUILDKIT=1 # enable buildkit for parallel builds
export COMPOSE_DOCKER_CLI_BUILD=1 # use docker cli for building

# Pull images from docker hub, but then retag for $cr_server for reuse and mirroring.
docker pull "docker.io/library/alpine:3.11" || true
docker tag "docker.io/library/alpine:3.11" "quay.io/wikipedialibrary/alpine:3.11"
docker pull "docker.io/library/debian:buster-slim" || true
docker tag "docker.io/library/debian:buster-slim" "quay.io/wikipedialibrary/debian:buster-slim"
docker pull "docker.io/library/mariadb:10" || true
docker tag "docker.io/library/mariadb:10" "quay.io/wikipedialibrary/mariadb:10"
docker pull "docker.io/library/nginx:latest" || true
docker tag "docker.io/library/nginx:latest" "quay.io/wikipedialibrary/nginx:latest"

# Build images with caching and then run the stack in docker-compose.
docker pull "quay.io/wikipedialibrary/twlight_base:branch_production" || true
docker pull "quay.io/wikipedialibrary/twlight_build:branch_production" || true
docker pull "quay.io/wikipedialibrary/twlight:branch_production" || true
docker pull "quay.io/wikipedialibrary/twlight_syslog:branch_production" || true

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
