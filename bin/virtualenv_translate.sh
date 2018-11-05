#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# By default we'll check unstaged changes, as this makes sense in development.
# But we also need to be able to check the most recent commit for CICD.
if [ "${1}" = "last-commit" ]
then
  refs='HEAD~1..HEAD'
else
  refs='--'
fi

source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh

# Get a list of languages, and add the reserved code for translation documentation.
langs=($(python manage.py diffsettings | grep '^LANGUAGES =' | grep -o "(u'[^']*'" | grep -o "'[^']*'"  | xargs))
langs+=('qqq')

makemessages() {
    echo "makemessages:"
    for locale in "${langs[@]}"
    do
      python manage.py makemessages --locale=${locale} || exit 1
      # Search and replace meaningless boilerplate information from headers.
      sed -i "s/# SOME DESCRIPTIVE TITLE./# TWLight ${locale} translation./" ${TWLIGHT_HOME}/locale/${locale}/LC_MESSAGES/django.po
      sed -i "s/# Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER/# Copyright (C) 2017 Wikimedia Foundation, Inc./" ${TWLIGHT_HOME}/locale/${locale}/LC_MESSAGES/django.po
      sed -i "s/# This file is distributed under the same license as the PACKAGE package./# This file is distributed under the same license as the TWLight package./" ${TWLIGHT_HOME}/locale/${locale}/LC_MESSAGES/django.po
      sed -i 's/# FIRST AUTHOR \<EMAIL\@ADDRESS\>, YEAR./#/' ${TWLIGHT_HOME}/locale/${locale}/LC_MESSAGES/django.po
      sed -i 's/# FIRST AUTHOR , YEAR./#/' ${TWLIGHT_HOME}/locale/${locale}/LC_MESSAGES/django.po
      sed -i 's/"Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\n"/#/' ${TWLIGHT_HOME}/locale/${locale}/LC_MESSAGES/django.po
      # Remove fuzzy header on non-english po files. This is a wikimedia-specific thing:
      # https://github.com/wikimedia/mediawiki-extensions-Translate/blob/master/ffs/GettextFFS.php#L108
      if [ "${locale}" != "en" ]
      then
	  # If fuzzy is in the header, remove the first instance of it.
	  if [ "$(head -5 ${TWLIGHT_HOME}/locale/${locale}/LC_MESSAGES/django.po | grep '#, fuzzy')"  ]
          then
	      fuzzy='#, fuzzy'
              sed -i "0,/${fuzzy}/s//#/" ${TWLIGHT_HOME}/locale/${locale}/LC_MESSAGES/django.po
          fi
      fi
    done
}

# Count the number of files searched by makemessages
# that have unstaged changes.
# https://docs.djangoproject.com/en/1.11/ref/django-admin/
message_files_changed=$(git diff --name-only ${refs} 'TWLight/*.html' 'TWLight/*.txt' 'TWLight/*.py' | wc -l)
# Count the number of translation files changed.
translation_files_changed=$(git diff --name-only ${refs} 'locale/*.po' | wc -l)

# Just hacked in here, but sometimes, you just want the stuff to execute.
if [ "${1}" = "force" ]
then
    message_files_changed=999
    translation_files_changed=0
fi

# If message files changed but no translations changed, make messages.
if [ "${message_files_changed}" -gt 0 ] && [ "${translation_files_changed}" -eq 0 ]
then
    makemessages
    # Recount the number of translation files changed.
    translation_files_changed=$(git diff --name-only -- ${refs} '*.po' | wc -l)
else
   echo "No translatable source files changed."
fi

# If translations changed, recompile messages.
if [ "${translation_files_changed}" -gt 0 ]
then
    echo "compilemessages:"
    # As of 2018-10-11, every commit from translatewiki.net contained an error
    # in at least one translation that prevented sucessful compliation. This
    # stalled out our deployment pipeline. Now we opportunistically build what
    # we can and silently pass over the rest.
    for locale in "${langs[@]}"
    do
      python manage.py compilemessages --locale=${locale} || :
    done
else
   echo "No translations changed."
fi
