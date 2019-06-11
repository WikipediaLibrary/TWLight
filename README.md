# README.md

The Wikipedia Library Card Platform app, available at http://wikipedialibrary.wmflabs.org.

## Quick Installation for Developers

- Get Docker and Docker Compose
- Fire up an empty TWLight instance `docker-compose build && docker-compose up`
- Run migrations `docker-compose exec twlight /app/bin/virtualenv_migrate.sh`
- See the thing running on [localhost](http://localhost/)
- Get an interactive shell `docker-compose exec twlight bash`

## Quick setup notes for Debian Servers
The staging environment is used in the following examples.

- Configure the upstream [Docker Repository](https://docs.docker.com/install/linux/docker-ce/debian/#install-using-the-repository) and install the latest version of Docker CE
- Install [Docker Compose](https://docs.docker.com/compose/install)
- Add yourself (or your shared system user) to the docker group `sudo usermod -a -G docker ${USER}` then logout and log back in.
- Clone this repository `git clone https://github.com/WikipediaLibrary/TWLight.git` (ideally into a shared directory like `/srv`) and checkout appropriate branch
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
- deploy for your environment `docker stack deploy -c docker-compose.yml -c docker-compose.staging.yml twlight_staging`
- Restore state from a backup `docker exec -t $(docker ps -q -f name=twlight_staging_twlight) /app/bin/virtualenv_restore.sh /app/backup/dd.hh.tar.gz`
- Get an interactive shell `docker exec -it $(docker ps -q -f name=twlight_staging_twlight) bash`
- Enable cron tasks for Django tasks and for applying updated Docker images:
```
> crontab -e
# Run django_cron tasks.
*/5 * * * *  docker exec -t $(docker ps -q -f name=twlight_staging_twlight) /app/bin/twlight_docker_entrypoint.sh python manage.py runcrons
# Update the running TWLight service if there is a new image.
*/5 * * * *  docker service update --image wikipedialibrary/twlight:branch_staging twlight_staging_twlight
```


See [twlight_puppet](https://github.com/WikipediaLibrary/twlight_puppet) if you want to set things up on WMF servers, and [twlight_vagrant](https://github.com/WikipediaLibrary/twlight_vagrant) if you want to change things.

[![Build Status](https://travis-ci.org/WikipediaLibrary/TWLight.svg?branch=master)](https://travis-ci.org/WikipediaLibrary/TWLight)

[![Dependabot Status](https://api.dependabot.com/badges/status?host=github&repo=WikipediaLibrary/TWLight)](https://dependabot.com)

[![Coverage Status](https://coveralls.io/repos/github/WikipediaLibrary/TWLight/badge.svg?branch=master)](https://coveralls.io/github/WikipediaLibrary/TWLight?branch=master) - master branch
