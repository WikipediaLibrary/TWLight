#!/usr/bin/env bash

source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh

# Count the number of files searched by makemessages
# that have unstaged changes.
# https://docs.djangoproject.com/en/1.11/ref/django-admin/
message_files_changed=$(git diff-files --name-only -- '*.html' '*.txt' '*.py' --porcelain | wc -l)
# Count the number of translation files changed.
translation_files_changed=$(git diff-files --name-only -- '*.po' --porcelain | wc -l)

# If any relevant files changed but no translation files changed,
# update translations.
if [ "${message_files_changed}" -gt 0 ] && [ "${translation_files_changed}" -eq 0 ]
then

    echo "makemessages"
    langs=($(python manage.py diffsettings | grep '^LANGUAGES =' | grep -o "(u'[^']*'" | grep -o "'[^']*'"  | xargs))
    for locale in "${langs[@]}"; do
      python manage.py makemessages --locale=${locale} || exit 1
    done
    python manage.py makemessages --locale=qqq || exit 1

    echo "compilemessages"
    python manage.py compilemessages || exit 1
else
   echo "No translatable source files changed."
fi
