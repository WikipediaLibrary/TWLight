#!/usr/bin/env bash
# Move into the repository and determine the git branch.
cd /srv/TWLight && branch=$(git rev-parse --abbrev-ref HEAD)
# Check for newer image
if [ -n "${branch+isset}" ] && docker pull wikipedialibrary/twlight:branch_${branch} | grep "Status: Downloaded newer image for wikipedialibrary/twlight:branch_${branch}" >/dev/null
then
    # Get any new docker-compose or script updates.
    git pull
    # Deploy the stack
    docker stack deploy -c docker-compose.yml -c docker-compose.${branch}.yml ${branch}
# Report if the local image is already up to date.
elif [ -n "${branch+isset}" ] && docker pull wikipedialibrary/twlight:branch_${branch} | grep "Status: Image is up to date for wikipedialibrary/twlight:branch_${branch}" >/dev/null
then
   echo "Up to date"
# Fail in any other circumstance.
else
   echo "Error"
   exit 1
fi
