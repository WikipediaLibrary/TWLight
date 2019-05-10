#!/usr/bin/env bash

# Only act if this is build is happening directly on the docker branch.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" = "docker" ]
then
  echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
  docker build -t wikipedialibrary/twlight:latest .
fi
