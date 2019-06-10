#!/usr/bin/env bash
set -euxo pipefail

docker build --cache-from "wikipedialibrary/twlight_base:${TRAVIS_BRANCH}" --target twlight_base --tag "twlight_base" .
docker build --cache-from "wikipedialibrary/twlight_build:${TRAVIS_BRANCH}" --target twlight_build --tag "twlight_build" .
docker build --cache-from "twlight_base" --target twlight_base --tag "wikipedialibrary/twlight_base:${TRAVIS_BRANCH}" .
docker build --cache-from "twlight_build" --target twlight_build --tag "wikipedialibrary/twlight_build:${TRAVIS_BRANCH}" .
docker build --cache-from "twlight_build"  --tag "wikipedialibrary/twlight:${TRAVIS_BRANCH}" .
docker-compose -f docker-compose.yml -f docker-compose.travis.yml up -d db twlight
