#!/usr/bin/env bash

docker pull "library/alpine:latest" || true
docker pull "wikipedialibrary/twlight_base:${BRANCH_TAG}" || true
docker pull "wikipedialibrary/twlight_build:${BRANCH_TAG}" || true
docker pull "wikipedialibrary/twlight:${BRANCH_TAG}" || true

docker build --cache-from "library/alpine:latest" \
             --cache-from "wikipedialibrary/twlight_base:${BRANCH_TAG}" \
             --target twlight_base \
             --tag "wikipedialibrary/twlight_base:${COMMIT_TAG}"  \
             --tag "wikipedialibrary/twlight_base:${BRANCH_TAG}"  \
             --tag "wikipedialibrary/twlight_base:${BUILD_TAG}" \
             .
docker build --cache-from "wikipedialibrary/twlight_base:${BRANCH_TAG}" \
             --cache-from "wikipedialibrary/twlight_build:${BRANCH_TAG}" \
             --target twlight_build \
             --tag "wikipedialibrary/twlight_build:${COMMIT_TAG}" \
             --tag "wikipedialibrary/twlight_build:${BRANCH_TAG}" \
             --tag "wikipedialibrary/twlight_build:${BUILD_TAG}" \
             .
docker build --cache-from "wikipedialibrary/twlight_base:${BRANCH_TAG}" \
             --cache-from "wikipedialibrary/twlight_build:${BRANCH_TAG}" \
             --cache-from "wikipedialibrary/twlight:${BRANCH_TAG}"  \
             --tag "wikipedialibrary/twlight:${COMMIT_TAG}" \
             --tag "wikipedialibrary/twlight:${BRANCH_TAG}" \
             --tag "wikipedialibrary/twlight:${BUILD_TAG}" \
             .

docker-compose -f docker-compose.yml -f docker-compose.travis.yml up -d db twlight
