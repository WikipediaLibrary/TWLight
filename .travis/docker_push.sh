#!/usr/bin/env bash

# Print Travis environment variables and migration count.
echo "TRAVIS_PULL_REQUEST: ${TRAVIS_PULL_REQUEST}"
echo "TRAVIS_TAG: ${TRAVIS_TAG}"
echo "TRAVIS_BRANCH: ${TRAVIS_BRANCH}"
echo "TWLIGHT_MISSING_MIGRATIONS: ${TWLIGHT_MISSING_MIGRATIONS}"
echo "TWLIGHT_TRANSLATION_FILES_CHANGED: ${TWLIGHT_TRANSLATION_FILES_CHANGED}"



# Only act if this is build was fired from a push and there are no missing migrations or changed translations.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ -n "${cr_server+isset}" && [ -n "${cr_username+isset}" ] && [ -n "${cr_password+isset}" ] && [ -n "${TWLIGHT_MISSING_MIGRATIONS+isset}" ] && [ "${TWLIGHT_MISSING_MIGRATIONS}" -eq 0 ] && [ "${TWLIGHT_TRANSLATION_FILES_CHANGED}" -eq 0 ]
then
  echo "$cr_password" | docker login $cr_server -u "$cr_username" --password-stdin

  docker push ${cr_server}/wikipedialibrary/alpine:3.11
  docker push ${cr_server}/wikipedialibrary/mariadb:10
  docker push ${cr_server}/wikipedialibrary/nginx:latest

  docker push ${cr_server}/wikipedialibrary/twlight_base:${COMMIT_TAG}
  docker push ${cr_server}/wikipedialibrary/twlight_base:${BRANCH_TAG}
  docker push ${cr_server}/wikipedialibrary/twlight_base:${BUILD_TAG}

  docker push ${cr_server}/wikipedialibrary/twlight_build:${COMMIT_TAG}
  docker push ${cr_server}/wikipedialibrary/twlight_build:${BRANCH_TAG}
  docker push ${cr_server}/wikipedialibrary/twlight_build:${BUILD_TAG}

  docker push ${cr_server}/wikipedialibrary/twlight:${COMMIT_TAG}
  docker push ${cr_server}/wikipedialibrary/twlight:${BRANCH_TAG}
  docker push ${cr_server}/wikipedialibrary/twlight:${BUILD_TAG}
fi
