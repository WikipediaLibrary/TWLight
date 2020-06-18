#!/usr/bin/env bash
#
# Runs Django tests (https://docs.djangoproject.com/en/1.11/topics/testing/)

set -euo pipefail

{
    # print the date for logging purposes
    echo [$(date)]

    # Load virtual environment
    if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
    then
        # Run linter
        echo "black --target-version py37 --check TWLight"
        if black --target-version py37 --check TWLight
        then
            # https://phabricator.wikimedia.org/T255167
            echo "Checking for localization issues"
            if _newline=$(find TWLight -name "*.py" -type f -print0 | xargs -0 pcregrep --color=always -Mn '_\(\n[ \t]*(.*)\n[^)]*\)')
            then
                echo "ERROR: ugettext messages can't be preceded by a newline, even though it's valid python"
                printf "${_newline}\n"
                exit 1
            else
                echo "No localization issues found"
                # Run test suite via coverage so we can get a report without having to run separate tests for it.
                DJANGO_LOG_LEVEL=CRITICAL DJANGO_SETTINGS_MODULE=TWLight.settings.local \
                coverage run --source TWLight manage.py test --keepdb --noinput
            fi
        else
            # If linting fails, offer some useful feedback to the user.
            black --target-version py37 --quiet --diff TWLight
            echo "You can fix these issues by running the following command on your host"
            echo "docker exec CONTAINER $(which black) -t py37 ${TWLIGHT_HOME}/TWLight"
            exit 1
        fi
    else
        exit 1
    fi
    # Submit coverage report to coveralls if we are running in the WikipediaLibrary Travis CI environment.
    if [ -n "${TRAVIS_BRANCH+isset}" ] && [ -n "${TRAVIS_JOB_ID+isset}" ] && [ -n "${COVERALLS_REPO_TOKEN+isset}" ]
    then
      coveralls
    fi
} 2>&1
