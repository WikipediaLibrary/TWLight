#!/usr/bin/env bash

if [ -z "$1" ] || [ -z "$2" ]
then
    echo "Usage: twlight_docker_deploy.sh \$env \$tag
    \$env    docker swarm environment (eg. staging | production).
    \$tag    docker hub image tag (eg. branch_staging | branch_production | latest)"
    exit 1;
fi

env=${1}
tag=${2}

# Move into the repository.
cd /srv/TWLight
# Check for newer image
pull=$(docker pull quay.io/wikipedialibrary/twlight:${tag})

# Pull swarm config updates and update the stack if there is a new image.
if echo ${pull} | grep "Status: Downloaded newer image for quay.io/wikipedialibrary/twlight:${tag}" >/dev/null
then
    git pull
    docker stack deploy -c docker-compose.yml -c docker-compose.${env}.yml ${env}
# Report if the local image is already up to date.
elif echo ${pull} | grep "Status: Image is up to date for quay.io/wikipedialibrary/twlight:${tag}" >/dev/null
then
   echo "Up to date"
# Fail in any other circumstance.
else
   echo "Error"
   exit 1
fi
