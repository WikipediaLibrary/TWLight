# README.md

The Wikipedia Library Card Platform app, available at http://wikipedialibrary.wmflabs.org.

## Quick Installation for Developers

- Get Docker and Docker Compose
- Copy the [example environment variables](conf/example.env) to `./.env`. This file contains settings you may wish to change.


## Management

- Fire up an empty TWLight instance `docker-compose build && docker-compose up`
- Run migrations `docker-compose exec twlight /app/bin/virtualenv_migrate.sh`
- See the thing running on [localhost](http://localhost/)

See [twlight_puppet](https://github.com/WikipediaLibrary/twlight_puppet) if you want to set things up on WMF servers, and [twlight_vagrant](https://github.com/WikipediaLibrary/twlight_vagrant) if you want to change things.

[![Build Status](https://travis-ci.org/WikipediaLibrary/TWLight.svg?branch=master)](https://travis-ci.org/WikipediaLibrary/TWLight)

[![Dependabot Status](https://api.dependabot.com/badges/status?host=github&repo=WikipediaLibrary/TWLight)](https://dependabot.com)

[![Coverage Status](https://coveralls.io/repos/github/WikipediaLibrary/TWLight/badge.svg?branch=master)](https://coveralls.io/github/WikipediaLibrary/TWLight?branch=master) - master branch
