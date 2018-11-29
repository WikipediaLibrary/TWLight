#!/usr/bin/env bash

# Print Travis environment variables and changed translation count.
echo "TRAVIS_PULL_REQUEST: ${TRAVIS_PULL_REQUEST}"
echo "TRAVIS_TAG: ${TRAVIS_TAG}"
echo "TRAVIS_BRANCH: ${TRAVIS_BRANCH}"
echo "TWLIGHT_CHANGED_TRANSLATIONS: ${TWLIGHT_CHANGED_TRANSLATIONS}"

# Only act if this is build was fired from a push to master and there are changed translations.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" = "master" ] && [ -n "${gh_bot_username+isset}" ] && [ -n "${gh_bot_token+isset}" ] && [ -n "${TWLIGHT_CHANGED_TRANSLATIONS+isset}" ] && [ "${TWLIGHT_CHANGED_TRANSLATIONS}" -gt 0 ]
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
    
    # Commit any changes to local master branch.
    git_commit() {

        # Checkout master branch
        git checkout master

        # Add and commit.
        git add 'locale/*/LC_MESSAGES/*.po'
        git add 'locale/*/LC_MESSAGES/*.mo'
        git commit --message "Travis build #${TRAVIS_BUILD_NUMBER} translations." || :
    }
    
    # Push to remote master branch.
    git_push() {
        # Fetch and merge before the push.
        # https://git-scm.com/docs/merge-strategies#merge-strategies-ours
        git fetch origin master --quiet

        # We'll probably be rewriting quite a few files, so if there is a conflict, keep the local version.
        git merge --strategy recursive -X ours origin/master --message "Travis build #${TRAVIS_BUILD_NUMBER} merged." --quiet

        # Push to remote master branch.
        git push origin master --quiet
    }

    git_config
    git_commit
    git_push && echo "Translations pushed to master."
else
    echo "Doesn't meet conditions for capturing changed translations. Skipping push to master."
fi
