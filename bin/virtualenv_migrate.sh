#!/usr/bin/env bash
#
# Runs the full Django migration process (https://docs.djangoproject.com/en/1.11/topics/migrations/)

# Load virtual environment and wait for db to come up.
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh && ${TWLIGHT_HOME}/bin/virtualenv_wait_for_db.sh
then
    # Run migrations
    echo "migrate"
    # We need to create initial revisions on fresh installs, which fail on
    # existing installs. Ignore exit status.
    python ${TWLIGHT_HOME}/manage.py createinitialrevisions || :
    python ${TWLIGHT_HOME}/manage.py makemigrations || exit 1

    if ! python ${TWLIGHT_HOME}/manage.py migrate; then
        # Sync any translation fields that were missed by migration.
        python ${TWLIGHT_HOME}/manage.py sync_translation_fields --noinput || exit 1
        python ${TWLIGHT_HOME}/manage.py migrate
    fi

    apps=($(python ${TWLIGHT_HOME}/manage.py diffsettings | grep 'TWLIGHT_APPS' | grep -o "'[^']*'" | xargs))
    for path in "${apps[@]}"; do
      # Strip 'TWLight.' from the front of each TWLIGHT_APP
      app=${path:8}
      # skip emails, graphs, and i18n
      if [ "${app}" = "emails" ] || [ "${app}" = "graphs" ] || [ "${app}" = "i18n" ]; then
        continue
      fi
      echo "createinitialrevisions ${app}"
      python ${TWLIGHT_HOME}/manage.py createinitialrevisions ${app} || :
      echo "makemigrations ${app}"
      python ${TWLIGHT_HOME}/manage.py makemigrations ${app} || exit 1
      echo "migrate ${app}"
      if ! python ${TWLIGHT_HOME}/manage.py migrate ${app}; then
          # Sync any translation fields that were missed by migration.
          python ${TWLIGHT_HOME}/manage.py sync_translation_fields --noinput || exit 1
          python ${TWLIGHT_HOME}/manage.py migrate ${app}
      fi
    done

    # Sync any translation fields that were missed by migration.
    echo "sync_translation_fields"
    python ${TWLIGHT_HOME}/manage.py sync_translation_fields --noinput || exit 1
else
    exit 1
fi
