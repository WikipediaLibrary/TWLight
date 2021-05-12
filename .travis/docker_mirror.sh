#!/usr/bin/env bash

# Print Travis environment variables and migration count.
echo "TRAVIS_EVENT_TYPE: ${TRAVIS_EVENT_TYPE}"

# Only act if this is build was fired from cron and we have container registry credentials
if [ "${TRAVIS_EVENT_TYPE}" = "cron" ] && [ -n "${cr_server+isset}" ] && [ -n "${cr_username+isset}" ] && [ -n "${cr_password+isset}" ]
then
  echo "$cr_password" | docker login $cr_server -u "$cr_username" --password-stdin

  # Pull images from docker hub, then retag for $cr_server for reuse and mirroring.
  declare -a images=("alpine:3.11" "debian:buster-slim" "mariadb:10" "nginx:latest" "python:3.7-slim-buster")
  for image in "${images[@]}"
  do
    docker pull docker.io/library/${image}
    docker tag docker.io/library/${image} ${cr_server}/wikipedialibrary/${image}
    docker push ${cr_server}/wikipedialibrary/${image}
  done
fi
