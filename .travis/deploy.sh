#!/bin/bash

# Print Travis environment variables.
echo "TRAVIS_PULL_REQUEST: ${TRAVIS_PULL_REQUEST}"
echo "TRAVIS_TAG: ${TRAVIS_TAG}"
echo "TRAVIS_BRANCH: ${TRAVIS_BRANCH}"

# Only act if this is build was fired from a push to master.
if [ "${TRAVIS_PULL_REQUEST}" = "false" ] && [ -z "${TRAVIS_TAG}" ] && [ "${TRAVIS_BRANCH}" = "master" ] && [ -n "${gh_bot_token+isset}" ]
then
    # Configure git user.
    setup_git() {
        git config --global user.email "deploy@travis-ci.org"
        git config --global user.name "Deployment Bot"
    }
    
    # Commit all changes to local production branch.
    commit_all_files() {
        git checkout -b production
        git add -A
        git commit --message "Travis Build: ${TRAVIS_BUILD_NUMBER}" || :
    }
    
    # Push changes to remote production branch.
    push_files() {
        git remote add origin https://WikipediaLibraryBot:${gh_bot_token}@github.com/WikipediaLibrary/TWLight.git > /dev/null 2>&1
        git push --quiet --set-upstream origin production && echo "Build pushed to production."
    }

    setup_git
    commit_all_files
    push_files
else
    echo "Doesn't meet conditions for deployment. Skipping push to production."
fi
