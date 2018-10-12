#!/usr/bin/env bash

# Search for missing migrations and count them.
export TWLIGHT_MISSING_MIGRATIONS=$(git ls-files --others --exclude-standard 'TWLight/*/migrations/*.py' | wc -l)

# Print Travis environment variables and migration count.
echo "TRAVIS_PULL_REQUEST: ${TRAVIS_PULL_REQUEST}"
echo "TRAVIS_TAG: ${TRAVIS_TAG}"
echo "TRAVIS_BRANCH: ${TRAVIS_BRANCH}"
echo "TWLIGHT_MISSING_MIGRATIONS: ${TWLIGHT_MISSING_MIGRATIONS}"

# Sync back to master if is build was fired from a push to master and there are missing migrations.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" = "master" ] && [ -n "${gh_bot_username+isset}" ] && [ -n "${gh_bot_token+isset}" ] && [ -n "${TWLIGHT_MISSING_MIGRATIONS+isset}" ] && [ "${TWLIGHT_MISSING_MIGRATIONS}" -gt 0 ]
then
   TWLIGHT_MISSING_MIGRATIONS=${TWLIGHT_MISSING_MIGRATIONS} ./migrations.sh
fi

# Deploy to production if is build was fired from a push to master and there are no missing migrations.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" = "master" ] && [ -n "${gh_bot_username+isset}" ] && [ -n "${gh_bot_token+isset}" ] && [ -n "${TWLIGHT_MISSING_MIGRATIONS+isset}" ] && [ "${TWLIGHT_MISSING_MIGRATIONS}" -eq 0 ]
then
   TWLIGHT_MISSING_MIGRATIONS=${TWLIGHT_MISSING_MIGRATIONS} ./production.sh
fi
