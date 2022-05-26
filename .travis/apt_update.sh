#!/usr/bin/env bash

sudo apt update -y
sudo apt install --only-upgrade docker-ce -y
# display docker version
docker info
