#!/usr/bin/env bash

# Search for missing migrations and count them.
export TWLIGHT_MISSING_MIGRATIONS=$(git ls-files --others --exclude-standard 'TWLight/*/migrations/*.py' | wc -l)

# Print Travis environment variables and migration count.
echo "TRAVIS_PULL_REQUEST: ${TRAVIS_PULL_REQUEST}"
echo "TRAVIS_TAG: ${TRAVIS_TAG}"
echo "TRAVIS_BRANCH: ${TRAVIS_BRANCH}"
echo "TWLIGHT_MISSING_MIGRATIONS: ${TWLIGHT_MISSING_MIGRATIONS}"

# Only act if this is build was fired from a push to master and there are missing migrations.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" = "master" ] && [ -n "${gh_bot_username+isset}" ] && [ -n "${gh_bot_token+isset}" ] && [ "${TWLIGHT_MISSING_MIGRATIONS}" -gt 0 ]
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
        git checkout -b master

        # Add and commit.
        git add 'TWLight/*/migrations/*.py'
        git commit --message "Travis build #${TRAVIS_BUILD_NUMBER} migrations." || :
    }
    
    # Push to remote master branch.
    git_push() {
        # Fetch and merge before the push.
        # https://git-scm.com/docs/merge-strategies#merge-strategies-theirs
        git fetch origin master --quiet

        # We should only be adding missing files, so if their's a conflict, keep the version from the remote.
        git merge --strategy recursive -X theirs origin/master --message "Travis build #${TRAVIS_BUILD_NUMBER} merged." --quiet

        # Push to remote master branch.
        git push origin master --quiet
    }

    git_config
    git_commit
    git_push && echo "Migrations pushed to master."
else
    echo "Doesn't meet conditions for capturing missing migrations. Skipping push to master."
fi
