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
        echo "black --target-version py38 --check TWLight"
        if black --target-version py38 --check TWLight
        then
            echo "${TWLIGHT_HOME}/tests/shunit/twlight_i18n_lint_test.sh"
            ${TWLIGHT_HOME}/tests/shunit/twlight_i18n_lint_test.sh

            # https://github.com/WikipediaLibrary/TWLight/wiki/Translation
            echo "Checking for localization issues"
            # TODO: add html jinja template checks.
            # find TWLight -type f \( -name "*.py" -o -name "*.html" \) -print0 | xargs -0 -I % ${TWLIGHT_HOME}/bin/twlight_i18n_lint.pl %
            find TWLight -type f \( -name "*.py" \) -print0 | xargs -0 -I % ${TWLIGHT_HOME}/bin/twlight_i18n_lint.pl %
            echo "No localization issues found"

            # Run test suite via coverage so we can get a report without having to run separate tests for it.
            DJANGO_LOG_LEVEL=CRITICAL DJANGO_SETTINGS_MODULE=TWLight.settings.local \
            coverage run --source TWLight manage.py test --keepdb --noinput --parallel --timing
        else
            # If linting fails, offer some useful feedback to the user.
            black --target-version py38 --quiet --diff TWLight
            echo "You can fix these issues by running the following command on your host"
            echo "docker exec CONTAINER $(which black) -t py38 ${TWLIGHT_HOME}/TWLight"
            exit 1
        fi
    else
        exit 1
    fi
} 2>&1
