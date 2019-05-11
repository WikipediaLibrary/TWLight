#!/usr/bin/env bash

# Only act if this is build is happening directly on a non-default branch.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" != "master" ]
then
  docker tag wikipedialibrary/twlight:local wikipedialibrary/twlight:${TRAVIS_BRANCH}
fi
