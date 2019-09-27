#!/usr/bin/env bash

# Checks to see if this is a WSL environment;
# If true, it sets environment variables in an attempt to make things universially worky.
# Originally motivated by Windows + Hyper-V + Docker + Vagrant struggles.
# Logic for check pulled from https://stackoverflow.com/a/43618657
# WSL-specific Vagrant information can be found here:
# https://www.vagrantup.com/docs/other/wsl.html
if grep -qE "(Microsoft|WSL)" /proc/version &> /dev/null ; then

  # Enable WSL vagrant
  export VAGRANT_WSL_ENABLE_WINDOWS_ACCESS="1"

  # Put the dotfiles in the WSL home directory so that ssh key permissions
  # may be set.
  here=$(basename $(pwd))
  export VAGRANT_DOTFILE_PATH="~/.vagrant/.${here}"

  # @TODO: make this check less brittle. Currenly only works with default install location.
  # Let WSL access Windows-side Docker if it's installed.
  if [[ -f '/mnt/c/Program Files/Docker/Docker/DockerCli.exe' || -f '/mnt/c/Program Files/Docker Toolbox/docker.exe' ]] ; then
      # Unset minikube variables that might make vagrant angry.
      unset DOCKER_TLS_VERIFY
      unset DOCKER_HOST
      unset DOCKER_CERT_PATH
      unset DOCKER_API_VERSION

      # Set variables to allow the docker service running in Windows to work in WSL.
      export DOCKER_HOST=tcp://127.0.0.1:2375
      export VAGRANT_DEFAULT_PROVIDER="docker"
  fi
else
  echo "Not a WSL environment."
fi
