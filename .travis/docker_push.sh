#!/usr/bin/env bash

# Print Travis environment variables and migration count.
echo "TRAVIS_PULL_REQUEST: ${TRAVIS_PULL_REQUEST}"
echo "TRAVIS_TAG: ${TRAVIS_TAG}"
echo "TRAVIS_BRANCH: ${TRAVIS_BRANCH}"
echo "TWLIGHT_MISSING_MIGRATIONS: ${TWLIGHT_MISSING_MIGRATIONS}"
echo "TWLIGHT_TRANSLATION_FILES_CHANGED: ${TWLIGHT_TRANSLATION_FILES_CHANGED}"



# Only act if this is build was fired from a push and there are no missing migrations or changed translations.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ -n "${DOCKER_USERNAME+isset}" ] && [ -n "${DOCKER_PASSWORD+isset}" ] && [ -n "${TWLIGHT_MISSING_MIGRATIONS+isset}" ] && [ "${TWLIGHT_MISSING_MIGRATIONS}" -eq 0 ] && [ "${TWLIGHT_TRANSLATION_FILES_CHANGED}" -eq 0 ]
then
  echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
  docker push wikipedialibrary/twlight_base:${COMMIT_TAG}
  docker push wikipedialibrary/twlight_base:${BRANCH_TAG}
  docker push wikipedialibrary/twlight_base:${BUILD_TAG}

  docker push wikipedialibrary/twlight_build:${COMMIT_TAG}
  docker push wikipedialibrary/twlight_build:${BRANCH_TAG}
  docker push wikipedialibrary/twlight_build:${BUILD_TAG}

  docker push wikipedialibrary/twlight:${COMMIT_TAG}
  docker push wikipedialibrary/twlight:${BRANCH_TAG}
  docker push wikipedialibrary/twlight:${BUILD_TAG}
fi
