# README.md

The Wikipedia Library Card Platform app, available at http://wikipedialibrary.wmflabs.org.

## Installation

- Get Docker and Docker Compose
- copy [twlight config](conf/local.twlight.env) to `./twlight.env` and edit as necessary.
- copy [db config](conf/local.db.env) to `./db.env` and edit as necessary.
- copy [host .env](conf/local..env) to `./.env`.
- configure your browser to use the [twlight proxy configuration file](conf/local.twlight.pac). If your browser expects a proxy configuration URL, you can enter a file url like: `file:///C:/<username>/TWLight/conf/local.twlight.pac`


## Management

- fire up an empty TWLight instance `docker-compose build && docker-compose up`
- run migrations `docker-compose exec twlight /app/bin/virtualenv_migrate.sh`

See [twlight_puppet](https://github.com/WikipediaLibrary/twlight_puppet) if you want to set things up on WMF servers, and [twlight_vagrant](https://github.com/WikipediaLibrary/twlight_vagrant) if you want to change things.

[![Build Status](https://travis-ci.org/WikipediaLibrary/TWLight.svg?branch=master)](https://travis-ci.org/WikipediaLibrary/TWLight)

[![Dependabot Status](https://api.dependabot.com/badges/status?host=github&repo=WikipediaLibrary/TWLight)](https://dependabot.com)

[![Coverage Status](https://coveralls.io/repos/github/WikipediaLibrary/TWLight/badge.svg?branch=master)](https://coveralls.io/github/WikipediaLibrary/TWLight?branch=master) - master branch
