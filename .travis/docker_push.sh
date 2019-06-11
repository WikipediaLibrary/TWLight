#!/usr/bin/env bash

# Only act if this is build is happening directly on a non-default branch.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" != "master" ]
then
  echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
  docker push wikipedialibrary/twlight_base:commit_${TRAVIS_COMMIT}
  docker push wikipedialibrary/twlight_base:branch_${TRAVIS_BRANCH}
  docker push wikipedialibrary/twlight_base:build_${TRAVIS_BUILD_NUMBER}

  docker push wikipedialibrary/twlight_build:commit_${TRAVIS_COMMIT}
  docker push wikipedialibrary/twlight_build:branch_${TRAVIS_BRANCH}
  docker push wikipedialibrary/twlight_build:build_${TRAVIS_BUILD_NUMBER}

  docker push wikipedialibrary/twlight:commit_${TRAVIS_COMMIT}
  docker push wikipedialibrary/twlight:branch_${TRAVIS_BRANCH}
  docker push wikipedialibrary/twlight:build_${TRAVIS_BUILD_NUMBER}
fi
