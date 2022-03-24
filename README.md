# README.md

The Wikipedia Library Card Platform app is available at http://wikipedialibrary.wmflabs.org.

## Quick Installation for Developers

- Get Docker and Docker Compose
- Fire up an empty TWLight instance `docker-compose build && docker-compose up`
- Run migrations `docker-compose exec twlight /app/bin/virtualenv_migrate.sh`
- See the thing running on [localhost](http://localhost/)
- Get an interactive shell `docker-compose exec twlight bash`

See the [Local setup](https://github.com/WikipediaLibrary/TWLight/wiki/Local-setup) Wiki page for more information.

## Documentation

Further project documentation is available in the [Wiki](https://github.com/WikipediaLibrary/TWLight/wiki). Our issue tracking takes place on the [Library-Card-Platform Phabricator](https://phabricator.wikimedia.org/project/board/2765/) board.

[![Build Status](https://travis-ci.com/WikipediaLibrary/TWLight.svg?branch=master)](https://travis-ci.com/github/WikipediaLibrary/TWLight)

[![Coveralls ](https://github.com/WikipediaLibrary/TWLight/actions/workflows/coveralls_check.yml/badge.svg)](https://github.com/WikipediaLibrary/TWLight/actions/workflows/coveralls_check.yml)
[![Coverage Status](https://coveralls.io/repos/github/WikipediaLibrary/TWLight/badge.svg?branch=master)](https://coveralls.io/github/WikipediaLibrary/TWLight?branch=master)
