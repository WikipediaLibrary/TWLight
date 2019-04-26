# README.md

The Wikipedia Library Card Platform app, available at http://wikipedialibrary.wmflabs.org.

## Quick Installation for Developers

- Get Docker and Docker Compose
- Fire up an empty TWLight instance `docker-compose build && docker-compose up`
- Run migrations `docker-compose exec twlight /app/bin/virtualenv_migrate.sh`
- See the thing running on [localhost](http://localhost/)
- Get an interactive shell `docker-compose exec twlight bash`

## Quick setup notes for Debian Servers

- Configure the upstream [Docker Repository](https://docs.docker.com/install/linux/docker-ce/debian/#install-using-the-repository) and install the latest version of Docker CE
- Install [Docker Compose](https://docs.docker.com/compose/install)
- Add yourself to the docker group `sudo usermod -a -G docker ${USER}` then logout and log back in.
- Clone this repository `git clone https://github.com/WikipediaLibrary/TWLight.git` and checkout appropriate branch
- `docker swarm init`
- Create secrets, but with real values:
```
printf "This is a secret" | docker secret create DJANGO_DB_NAME -
printf "This is a secret" | docker secret create DJANGO_DB_USER -
printf "This is a secret" | docker secret create DJANGO_DB_PASSWORD -
printf "This is a secret" | docker secret create MYSQL_ROOT_PASSWORD -
printf "This is a secret" | docker secret create SECRET_KEY -
printf "This is a secret" | docker secret create TWLIGHT_OAUTH_CONSUMER_KEY -
printf "This is a secret" | docker secret create TWLIGHT_OAUTH_CONSUMER_SECRET -
```
- build for your environment, here's staging `docker-compose -f docker-compose.yml -f docker-compose.staging.yml build`
- deploy for your environment, here's staging `docker stack deploy -c docker-compose.yml -c docker-compose.staging.yml twlight_stack`
- Restore state from a backup `docker exec -t $(docker ps -q -f name=twlight_stack_twlight) /app/bin/virtualenv_restore.sh /app/backup/dd.hh.tar.gz`
- Run migrations `docker exec -t $(docker ps -q -f name=twlight_stack_twlight) /app/bin/virtualenv_migrate.sh`
- Get an interactive shell `docker exec -it $(docker ps -q -f name=twlight_stack_twlight) bash`


See [twlight_puppet](https://github.com/WikipediaLibrary/twlight_puppet) if you want to set things up on WMF servers, and [twlight_vagrant](https://github.com/WikipediaLibrary/twlight_vagrant) if you want to change things.

[![Build Status](https://travis-ci.org/WikipediaLibrary/TWLight.svg?branch=master)](https://travis-ci.org/WikipediaLibrary/TWLight)

[![Dependabot Status](https://api.dependabot.com/badges/status?host=github&repo=WikipediaLibrary/TWLight)](https://dependabot.com)

[![Coverage Status](https://coveralls.io/repos/github/WikipediaLibrary/TWLight/badge.svg?branch=master)](https://coveralls.io/github/WikipediaLibrary/TWLight?branch=master) - master branch
