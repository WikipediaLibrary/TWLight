#!/usr/bin/env bash

# Count the number of files searched by makemessages
# that were changed in the last commit.
# https://docs.djangoproject.com/en/1.11/ref/django-admin/
message_files_changed=$(git diff --name-only HEAD~1..HEAD -- '*.html' '*.txt' '*.py' | wc -l)
translation_files_changed=$(git diff --name-only HEAD~1..HEAD -- '*.po' | wc -l)

# If any relevant files changed but no translation files changed,
# update translations.
if [ "${message_files_changed}" -gt 0 ] && [ "${translation_files_changed}" -eq 0 ]
then
    # Compile translations
    echo "makemessages"
    langs=($(python manage.py diffsettings | grep '^LANGUAGES =' | grep -o "(u'[^']*'" | grep -o "'[^']*'"  | xargs))
    for locale in "${langs[@]}"; do
      python manage.py makemessages --locale=${locale} || exit 1
    done
    python manage.py makemessages --locale=qqq || exit 1
    
    echo "compilemessages"
    python manage.py compilemessages || exit 1
fi
