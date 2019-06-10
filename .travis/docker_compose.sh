#!/usr/bin/env bash

docker pull "library/alpine:latest" || true
docker pull "wikipedialibrary/twlight_base:${TRAVIS_BRANCH}" || true
docker pull "wikipedialibrary/twlight_build:${TRAVIS_BRANCH}" || true

docker build --cache-from "library/alpine:latest" --cache-from "wikipedialibrary/twlight_base:${TRAVIS_BRANCH}" --target twlight_base --tag "wikipedialibrary/twlight_base:${TRAVIS_BRANCH}" .
docker build --cache-from "wikipedialibrary/twlight_base:${TRAVIS_BRANCH}" --cache-from "wikipedialibrary/twlight_build:${TRAVIS_BRANCH}" --target twlight_build --tag "wikipedialibrary/twlight_build:${TRAVIS_BRANCH}" .
docker build --cache-from "wikipedialibrary/twlight_base:${TRAVIS_BRANCH}" --cache-from "wikipedialibrary/twlight_build:${TRAVIS_BRANCH}" --cache-from "wikipedialibrary/twlight:${TRAVIS_BRANCH}"  --tag "wikipedialibrary/twlight:${TRAVIS_BRANCH}" .

docker-compose -f docker-compose.yml -f docker-compose.travis.yml up -d db twlight
