#!/usr/bin/env bash

# Print Travis environment variables.
echo "TRAVIS_PULL_REQUEST: ${TRAVIS_PULL_REQUEST}"
echo "TRAVIS_TAG: ${TRAVIS_TAG}"
echo "TRAVIS_BRANCH: ${TRAVIS_BRANCH}"

# Only act if this is build was fired from a push to master.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" = "master" ] && [ -n "${gh_bot_username+isset}" ] && [ -n "${gh_bot_token+isset}" ]
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
    
    # Commit any changes to local production branch.
    git_commit() {
        # Capture collectedstatic for deployment.
        sed -i '/^collectedstatic\/$/d' ./.gitignore

        # Checkout production branch
        git checkout -b production

        # Add and commit.
        git add -A
        git commit --message "Travis build #${TRAVIS_BUILD_NUMBER} changes." || :
    }
    
    # Push to remote production branch.
    git_push() {
        # Fetch and merge before the push.
        # https://git-scm.com/docs/merge-strategies#merge-strategies-ours
        git fetch origin production --quiet

        # We really don't care what was in the production branch before.
        git merge --strategy ours origin/production --message "Travis build #${TRAVIS_BUILD_NUMBER} deployed." --quiet

        # Push to remote production branch.
        git push origin production --quiet
    }

    git_config
    git_commit
    git_push && echo "Build pushed to production."
else
    echo "Doesn't meet conditions for deployment. Skipping push to production."
fi
