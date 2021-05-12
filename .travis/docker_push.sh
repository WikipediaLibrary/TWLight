#!/usr/bin/env bash

# Print Travis environment variables and migration count.
echo "TRAVIS_EVENT_TYPE: ${TRAVIS_EVENT_TYPE}"
echo "TRAVIS_TAG: ${TRAVIS_TAG}"
echo "TRAVIS_BRANCH: ${TRAVIS_BRANCH}"
echo "TWLIGHT_MISSING_MIGRATIONS: ${TWLIGHT_MISSING_MIGRATIONS}"
echo "TWLIGHT_TRANSLATION_FILES_CHANGED: ${TWLIGHT_TRANSLATION_FILES_CHANGED}"

# Only act if this is build was fired from a push and there are no missing migrations or changed translations.
if [ "${TRAVIS_EVENT_TYPE}" = "push" ] && [ -z "${TRAVIS_TAG}" ] && [ -n "${cr_server+isset}" ] && [ -n "${cr_username+isset}" ] && [ -n "${cr_password+isset}" ] && [ -n "${TWLIGHT_MISSING_MIGRATIONS+isset}" ] && [ "${TWLIGHT_MISSING_MIGRATIONS}" -eq 0 ] && [ "${TWLIGHT_TRANSLATION_FILES_CHANGED}" -eq 0 ]
then
  echo "$cr_password" | docker login $cr_server -u "$cr_username" --password-stdin

  # Push built images to ${cr_server}
  declare -a repositories=("twlight_base" "twlight_build" "twlight" "twlight_syslog")
  for repository in "${repositories[@]}"
  do
    docker push ${cr_server}/wikipedialibrary/${repository}:${COMMIT_TAG}
    docker push ${cr_server}/wikipedialibrary/${repository}:${BRANCH_TAG}
    docker push ${cr_server}/wikipedialibrary/${repository}:${BUILD_TAG}
  done
fi
