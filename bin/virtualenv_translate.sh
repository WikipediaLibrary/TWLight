#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh

makemessages() {
    echo "makemessages"
    langs=($(python manage.py diffsettings | grep '^LANGUAGES =' | grep -o "(u'[^']*'" | grep -o "'[^']*'"  | xargs))
    langs+=('qqq')
    for locale in "${langs[@]}"; do
      python manage.py makemessages --locale=${locale} || exit 1
      # Search and replace meaningless boilerplate information from headers.
      sed -i "s/# SOME DESCRIPTIVE TITLE./# TWLlight ${locale} translation./" ${TWLIGHT_HOME}/locale/${locale}/LC_MESSAGES/django.po
      # @TODO do this with Python instead of Perl to avoid extra dependencies.
      # multiline text munging is just so handy in Perl.
      perl -i -0pe 's/# FIRST AUTHOR \<EMAIL\@ADDRESS\>, YEAR.\n#\n#, fuzzy/#/' ${TWLIGHT_HOME}/locale/${locale}/LC_MESSAGES/django.po
    done
}

# Count the number of files searched by makemessages
# that have unstaged changes.
# https://docs.djangoproject.com/en/1.11/ref/django-admin/
message_files_changed=$(git diff-files --name-only -- '*.html' '*.txt' '*.py' --porcelain | wc -l)
# Count the number of translation files changed.
translation_files_changed=$(git diff-files --name-only -- '*.po' --porcelain | wc -l)

# If message files changed but no translations changed, make messages.
if [ "${message_files_changed}" -gt 0 ] && [ "${translation_files_changed}" -eq 0 ]
then
    makemessages
    # Recount the number of translation files changed.
    translation_files_changed=$(git diff-files --name-only -- '*.po' --porcelain | wc -l)
else
   echo "No translatable source files changed."
fi

# If translations changed, recompile messages.
if [ "${translation_files_changed}" -gt 0 ]
then
    echo "compilemessages"
    python manage.py compilemessages || exit 1
else
   echo "No translations changed."
fi
