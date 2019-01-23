#!/usr/bin/env bash
#
# Runs the full Django migration process (https://docs.djangoproject.com/en/1.11/topics/migrations/)

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    # Run migrations
    echo "migrate"
    # We need to create initial revisions on fresh installs, which fail on
    # existing installs. Ignore exit status.
    python manage.py createinitialrevisions || :
    python manage.py makemigrations || exit 1

    if ! python manage.py migrate; then
        # Sync any translation fields that were missed by migration.
        python manage.py sync_translation_fields --noinput || exit 1
        python manage.py migrate
    fi

    apps=($(python manage.py diffsettings | grep 'TWLIGHT_APPS' | grep -o "'[^']*'" | xargs))
    for path in "${apps[@]}"; do
      # Strip 'TWLight.' from the front of each TWLIGHT_APP
      app=${path:8}
      # skip emails, graphs, and i18n
      if [ "${app}" = "emails" ] || [ "${app}" = "graphs" ] || [ "${app}" = "i18n" ]; then
        continue
      fi
      echo "createinitialrevisions ${app}"
      python manage.py createinitialrevisions ${app} || :
      echo "makemigrations ${app}"
      python manage.py makemigrations ${app} || exit 1
      echo "migrate ${app}"
      if ! python manage.py migrate ${app}; then
          # Sync any translation fields that were missed by migration.
          python manage.py sync_translation_fields --noinput || exit 1
          python manage.py migrate ${app}
      fi
    done

    # Sync any translation fields that were missed by migration.
    echo "sync_translation_fields"
    python manage.py sync_translation_fields --noinput || exit 1
else
    exit 1
fi
