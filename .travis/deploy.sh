#!/usr/bin/env bash

# Search for missing migrations and count them.
export TWLIGHT_MISSING_MIGRATIONS=$(git ls-files --others --exclude-standard 'TWLight/*/migrations/*.py' | wc -l)

# Search for new translation files and count them.
TWLIGHT_TRANSLATION_FILES_ADDED=$(git ls-files --others --exclude-standard 'locale/*/LC_MESSAGES/django.po' | wc -l)

# Search for updated translation files and count them.
TWLIGHT_TRANSLATION_FILES_UPDATED=$(git diff --name-only -- 'locale/*/LC_MESSAGES/django.po' | wc -l)

# Add new and updated to get change count.
TWLIGHT_TRANSLATION_FILES_CHANGED=$((TWLIGHT_TRANSLATION_FILES_ADDED+TWLIGHT_TRANSLATION_FILES_UPDATED))


# Print Travis environment variables and migration count.
echo "TRAVIS_PULL_REQUEST: ${TRAVIS_PULL_REQUEST}"
echo "TRAVIS_TAG: ${TRAVIS_TAG}"
echo "TRAVIS_BRANCH: ${TRAVIS_BRANCH}"
echo "TWLIGHT_MISSING_MIGRATIONS: ${TWLIGHT_MISSING_MIGRATIONS}"
echo "TWLIGHT_TRANSLATION_FILES_CHANGED: ${TWLIGHT_TRANSLATION_FILES_CHANGED}"

# Sync back to master if is build was fired from a push to master and there are missing migrations.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" = "master" ] && [ -n "${gh_bot_username+isset}" ] && [ -n "${gh_bot_token+isset}" ] && [ -n "${TWLIGHT_MISSING_MIGRATIONS+isset}" ] && [ "${TWLIGHT_MISSING_MIGRATIONS}" -gt 0 ]
then
   TWLIGHT_MISSING_MIGRATIONS=${TWLIGHT_MISSING_MIGRATIONS} .travis/./migrations.sh
fi

# Sync back to master if this is build was fired from a push to master and there are changed translations.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" = "master" ] && [ -n "${gh_bot_username+isset}" ] && [ -n "${gh_bot_token+isset}" ] && [ -n "${TWLIGHT_TRANSLATION_FILES_CHANGED+isset}" ] && [ "${TWLIGHT_TRANSLATION_FILES_CHANGED}" -gt 0 ]
then
   TWLIGHT_TRANSLATION_FILES_CHANGED=${TWLIGHT_TRANSLATION_FILES_CHANGED} .travis/./translations.sh
fi


# Deploy to production if is build was fired from a push to master and there are no missing migrations or changed translations.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" = "master" ] && [ -n "${gh_bot_username+isset}" ] && [ -n "${gh_bot_token+isset}" ] && [ -n "${TWLIGHT_MISSING_MIGRATIONS+isset}" ] && [ "${TWLIGHT_MISSING_MIGRATIONS}" -eq 0 ] && [ "${TWLIGHT_TRANSLATION_FILES_CHANGED}" -eq 0 ]
then
   TWLIGHT_MISSING_MIGRATIONS=${TWLIGHT_MISSING_MIGRATIONS} TWLIGHT_TRANSLATION_FILES_CHANGED=${TWLIGHT_TRANSLATION_FILES_CHANGED} .travis/./production.sh
fi
