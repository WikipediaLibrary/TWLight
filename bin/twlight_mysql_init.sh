#!/usr/bin/env bash

if  [ ! -n "${DJANGO_DB_NAME+isset}" ]
then
    DJANGO_DB_NAME=$(cat /run/secrets/DJANGO_DB_NAME)
fi

if  [ ! -n "${DJANGO_DB_USER+isset}" ]
then
    DJANGO_DB_USER=$(cat /run/secrets/DJANGO_DB_USER)
fi

if  [ ! -n "${DJANGO_DB_PASSWORD+isset}" ]
then
    DJANGO_DB_PASSWORD=$(cat /run/secrets/DJANGO_DB_PASSWORD)
fi

if  [ ! -n "${MYSQL_ROOT_PASSWORD+isset}" ]
then
    MYSQL_ROOT_PASSWORD=$(cat /run/secrets/MYSQL_ROOT_PASSWORD)
fi

if  [ -n "${MYSQL_ROOT_PASSWORD+isset}" ]
then
    mysql_cmd="mysql -u root -p${MYSQL_ROOT_PASSWORD}"
else
    mysql_cmd="mysql"
fi

${mysql_cmd} <<EOF
CREATE DATABASE IF NOT EXISTS ${DJANGO_DB_NAME};
CREATE DATABASE IF NOT EXISTS test_${DJANGO_DB_NAME};
GRANT ALL PRIVILEGES on \`${DJANGO_DB_NAME}\`.* to ${DJANGO_DB_USER}@'%' IDENTIFIED BY '${DJANGO_DB_PASSWORD}';
GRANT ALL PRIVILEGES on \`test\_${DJANGO_DB_NAME}\`.* to ${DJANGO_DB_USER}@'%' IDENTIFIED BY '${DJANGO_DB_PASSWORD}';
GRANT ALL PRIVILEGES on \`test\_${DJANGO_DB_NAME}\_%\`.* to ${DJANGO_DB_USER}@'%' IDENTIFIED BY '${DJANGO_DB_PASSWORD}';
EOF
