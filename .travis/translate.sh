#!/usr/bin/env bash

# Compile translations
echo "makemessages"
langs=($(python manage.py diffsettings | grep '^LANGUAGES =' | grep -o "(u'[^']*'" | grep -o "'[^']*'"  | xargs))
for locale in "${langs[@]}"; do
  python manage.py makemessages --locale=${locale} || exit 1
done
python manage.py makemessages --locale=qqq || exit 1

echo "compilemessages"
python manage.py compilemessages || exit 1
