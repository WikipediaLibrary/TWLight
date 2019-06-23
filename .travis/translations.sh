#!/usr/bin/env bash

# Print Travis environment variables and changed translation count.
echo "TRAVIS_PULL_REQUEST: ${TRAVIS_PULL_REQUEST}"
echo "TRAVIS_TAG: ${TRAVIS_TAG}"
echo "TRAVIS_BRANCH: ${TRAVIS_BRANCH}"
echo "TWLIGHT_TRANSLATION_FILES_CHANGED: ${TWLIGHT_TRANSLATION_FILES_CHANGED}"

# Only act if this is build was fired from a push and there are changed translations.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ -n "${gh_bot_username+isset}" ] && [ -n "${gh_bot_token+isset}" ] && [ -n "${TWLIGHT_TRANSLATION_FILES_CHANGED+isset}" ] && [ "${TWLIGHT_TRANSLATION_FILES_CHANGED}" -gt 0 ]
then
    # Configure git.
    git_config() {
        # Configure user.
        git config --global user.email "deploy@travis-ci.org"
        git config --global user.name "Deployment Bot"

        # Remove the anonymous origin.
        git remote rm origin

        # Add our authenticated origin using encrypted travis environment variables.
        git remote add origin https://${gh_bot_username}:${gh_bot_token}@github.com/${TRAVIS_REPO_SLUG}.git > /dev/null 2>&1
    }

    # Commit any changes to local branch.
    git_commit() {
        # Checkout branch
        git checkout ${TRAVIS_BRANCH}

        # Add and commit.
        git add 'locale/*/LC_MESSAGES/*.po'
        git add 'locale/*/LC_MESSAGES/*.mo'
        git commit --message "Travis build #${TRAVIS_BUILD_NUMBER} translations." || :
    }

    # Push to remote ${TRAVIS_BRANCH} branch.
    git_push() {
        # Fetch and merge before the push.
        # https://git-scm.com/docs/merge-strategies#merge-strategies-ours
        git fetch origin ${TRAVIS_BRANCH} --quiet

        # We'll probably be rewriting quite a few files, so if there is a conflict, keep the local version.
        git merge --strategy recursive -X ours origin/${TRAVIS_BRANCH} --message "Travis build #${TRAVIS_BUILD_NUMBER} merged." --quiet

        # Push to remote ${TRAVIS_BRANCH} branch.
        git push origin ${TRAVIS_BRANCH} --quiet
    }

    git_config
    git_commit
    git_push && echo "Translations pushed to ${TRAVIS_BRANCH}."
else
    echo "Doesn't meet conditions for capturing changed translations. Skipping push to ${TRAVIS_BRANCH}."
fi
