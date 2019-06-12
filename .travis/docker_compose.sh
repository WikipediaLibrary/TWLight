#!/usr/bin/env bash

docker pull "library/alpine:latest" || true
docker pull "wikipedialibrary/twlight_base:branch_${TRAVIS_BRANCH}" || true
docker pull "wikipedialibrary/twlight_build:branch_${TRAVIS_BRANCH}" || true
docker pull "wikipedialibrary/twlight:branch_${TRAVIS_BRANCH}" || true

docker build --cache-from "library/alpine:latest" \
             --cache-from "wikipedialibrary/twlight_base:branch_${TRAVIS_BRANCH}" \
             --target twlight_base \
             --tag "wikipedialibrary/twlight_base:commit_${TRAVIS_COMMIT}"  \
             --tag "wikipedialibrary/twlight_base:branch_${TRAVIS_BRANCH}"  \
             --tag "wikipedialibrary/twlight_base:build_${TRAVIS_BUILD_NUMBER}" \
             .
docker build --cache-from "wikipedialibrary/twlight_base:branch_${TRAVIS_BRANCH}" \
             --cache-from "wikipedialibrary/twlight_build:branch_${TRAVIS_BRANCH}" \
             --target twlight_build \
             --tag "wikipedialibrary/twlight_build:commit_${TRAVIS_COMMIT}" \
             --tag "wikipedialibrary/twlight_build:branch_${TRAVIS_BRANCH}" \
             --tag "wikipedialibrary/twlight_build:build_${TRAVIS_BUILD_NUMBER}" \
             .
docker build --cache-from "wikipedialibrary/twlight_base:branch_${TRAVIS_BRANCH}" \
             --cache-from "wikipedialibrary/twlight_build:branch_${TRAVIS_BRANCH}" \
             --cache-from "wikipedialibrary/twlight:branch_${TRAVIS_BRANCH}"  \
             --tag "wikipedialibrary/twlight:commit_${TRAVIS_COMMIT}" \
             --tag "wikipedialibrary/twlight:branch_${TRAVIS_BRANCH}" \
             --tag "wikipedialibrary/twlight:build_${TRAVIS_BUILD_NUMBER}" \
             .

docker-compose -f docker-compose.yml -f docker-compose.travis.yml up -d db twlight
