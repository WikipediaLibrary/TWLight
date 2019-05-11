#!/usr/bin/env bash

echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
docker pull wikipedialibrary/twlight:${TRAVIS_BRANCH} || true
