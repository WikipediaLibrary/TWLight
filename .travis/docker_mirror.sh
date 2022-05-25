#!/usr/bin/env bash

# Print Travis environment variables and migration count.
echo "TRAVIS_EVENT_TYPE: ${TRAVIS_EVENT_TYPE}"

# Only act if this is build was fired from cron and we have container registry credentials
if [ -n "${cr_server+isset}" ] && [ -n "${cr_username+isset}" ] && [ -n "${cr_password+isset}" ]
then
  echo "$cr_password" | docker login $cr_server -u "$cr_username" --password-stdin

  # Pull images from docker hub, then retag for $cr_server for reuse and mirroring.
  declare -a images=("alpine:3.11" "debian:buster-slim" "nginx:latest" "python:3.8-buster" "python:3.7-slim-buster")
  for image in "${images[@]}"
  do
    docker pull docker.io/library/${image}
    docker tag docker.io/library/${image} ${cr_server}/wikipedialibrary/${image}
    docker push ${cr_server}/wikipedialibrary/${image}
  done
  # Per https://github.com/MariaDB/mariadb-docker/issues/434, mariadb must be
  # pulled from own mariadb quay.io
  docker pull quay.io/mariadb-foundation/mariadb-devel:10.7
  docker tag quay.io/mariadb-foundation/library/mariadb-devel:10.7 ${cr_server}/wikipedialibrary/mariadb-devel:10.7
  docker push ${cr_server}/wikipedialibrary/mariadb-devel:10.7
fi
