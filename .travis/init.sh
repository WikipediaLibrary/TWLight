#!/usr/bin/env bash

# Install cssjanus.
mkdir -p ~/node_modules
npm install --prefix ~ cssjanus

# Create databases.
mysql < .travis/db.sql

# Write config file.
cp .travis/local_vars.py TWLight/settings/local_vars.py

# Ensure static dir exists.
mkdir -p TWLight/collectedstatic

# Initialize Django app:
# make migrations
python manage.py makemigrations

# Migrate and sync translation fields.
python manage.py migrate || bash -c "python manage.py sync_translation_fields --noinput && python manage.py migrate"

# Compile translations. Slightly involved due to this being a Wikimedia project.
.travis/./translate.sh

# Generate right to left css
node bin/twlight_cssjanus.js

# Collect static assets
python manage.py collectstatic --noinput --clear
