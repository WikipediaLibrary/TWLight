#!/usr/bin/env bash

docker pull "wikipedialibrary/twlight:${TRAVIS_BRANCH}" || :
docker build --pull --cache-from "wikipedialibrary/twlight:${TRAVIS_BRANCH}" --tag "wikipedialibrary/twlight:${TRAVIS_BRANCH}" .
