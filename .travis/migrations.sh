#!/usr/bin/env bash

# Search for missing migrations and count them.
missing_migrations_count=$(git ls-files --others --exclude-standard 'TWLight/*/migrations/*.py' | wc -l)

# Print Travis environment variables and migration count.
echo "TRAVIS_PULL_REQUEST: ${TRAVIS_PULL_REQUEST}"
echo "TRAVIS_TAG: ${TRAVIS_TAG}"
echo "TRAVIS_BRANCH: ${TRAVIS_BRANCH}"
echo "missing_migrations_count: ${missing_migrations_count}"

# Only act if this is build was fired from a push to master and there are missing migrations.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" = "master" ] && [ -n "${gh_bot_username+isset}" ] && [ -n "${gh_bot_token+isset}" ] && [ "${missing_migrations_count}" -gt 0 ]
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
        # Push to remote master branch.
        git push origin master --quiet
    }

    git_config
    git_commit
    git_push && echo "Migrations pushed to master."
else
    echo "Doesn't meet conditions for capturing missing migrations. Skipping push to master."
fi
