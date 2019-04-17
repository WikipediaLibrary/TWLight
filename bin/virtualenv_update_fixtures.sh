#!/usr/bin/env bash

set -eo pipefail

# Updates fixtures that already exists and creates ones that don't already
# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

PATH=/usr/local/bin:/usr/bin:/bin:/sbin:$PATH

mysqlhost=localhost
mysqldb=twlight
mysqluser=twlight
mysqlpass=$(cat ${TWLIGHT_HOME}/TWLight/settings/${TWLIGHT_ENV}_vars.py | grep ^MYSQL_PASSWORD | cut -d "=" -f 2 | xargs)

# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    echo "Updating/creating fixtures (dumpdata)"
    mysql -N -h "${mysqlhost}" -u "${mysqluser}" -p"${mysqlpass}" "${mysqldb}" -e "SELECT id FROM resources_partner" | while read id; do
        python manage.py dumpdata resources.partner --format yaml --pks $id > "TWLight/resources/fixtures/partners/$id.yaml"
        python bin/exclude_certain_fields.py $id
        echo "Dumping data for partner $id"
    done
    
    mysql -N -h "${mysqlhost}" -u "${mysqluser}" -p"${mysqlpass}" "${mysqldb}" -e "SELECT id FROM resources_stream" | while read id; do
        python manage.py dumpdata resources.stream --format yaml --pks $id > "TWLight/resources/fixtures/streams/$id.yaml"
        echo "Dumping data for stream $id"
    done 
    echo "Dumping complete" || exit
else
    exit 1
fi
