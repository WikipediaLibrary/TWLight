#!/usr/bin/env bash

# Only act if this is build is happening directly on a non-default branch.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" != "master" ]
then
  echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
  docker push wikipedialibrary/twlight:${TRAVIS_BRANCH}
fi
