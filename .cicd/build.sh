#!/usr/bin/env bash
set -euo pipefail
export DOCKER_BUILDKIT=1 # enable buildkit for parallel builds
export COMPOSE_DOCKER_CLI_BUILD=1 # use docker cli for building

branch="${1//[\/]/-}"
commit="${2}"

chown -R root:root .
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.cicd.yml build twlight syslog 2>/dev/null
docker tag "quay.io/wikipedialibrary/twlight:local" "quay.io/wikipedialibrary/twlight:branch_${branch}"
docker tag "quay.io/wikipedialibrary/twlight:local" "quay.io/wikipedialibrary/twlight:commit_${commit}"
docker tag "quay.io/wikipedialibrary/twlight_syslog:local" "quay.io/wikipedialibrary/twlight_syslog:branch_${branch}"
docker tag "quay.io/wikipedialibrary/twlight_syslog:local" "quay.io/wikipedialibrary/twlight_syslog:commit_${commit}"
docker compose up -d db twlight
