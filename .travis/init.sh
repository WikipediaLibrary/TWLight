#!/usr/bin/env bash

# Create databases.
mysql < .travis/init_db.sql

# Write config file.
cp TWLight/settings/travis_vars.py TWLight/settings/local_vars.py

# Initialize Django app: make migrations, migrate, sync translations, collect static.
python manage.py makemigrations
python manage.py migrate || bash -c "python manage.py sync_translation_fields --noinput && python manage.py migrate"
python manage.py collectstatic --noinput --clear
