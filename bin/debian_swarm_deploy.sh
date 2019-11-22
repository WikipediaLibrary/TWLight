#!/usr/bin/env bash
# Installs dependencies and deploys TWLight to a single Debian host.

set -euo pipefail

# Ensure the docker repo will be usable.
apt install -y apt-transport-https ca-certificates curl gnupg2 software-properties-common
# Add the apt key
curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -
# Add the apt repo
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"
# Update
apt update && apt upgrade -y

# Install docker
apt install -y docker-ce docker-ce-cli containerd.io
curl -L "https://github.com/docker/compose/releases/download/1.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Add twlight user
adduser twlight
usermod -a -G docker twlight

# Pull TWLight code and make twlight user the owner
cd /srv
git clone https://github.com/WikipediaLibrary/TWLight.git
chown -R twlight:twlight TWLight

sudo su twlight bash << EOF
cd /srv/TWLight
# Get on correct branch
echo "Enter git branch:"
read TWLIGHT_GIT_BRANCH
git checkout "${TWLIGHT_GIT_BRANCH}" && git pull

docker swarm init

echo "Enter DJANGO_DB_NAME:"
read DJANGO_DB_NAME
echo "Enter DJANGO_DB_USER:"
read DJANGO_DB_USER
echo "Enter DJANGO_DB_PASSWORD:"
read DJANGO_DB_PASSWORD
echo "Enter MYSQL_ROOT_PASSWORD:"
read MYSQL_ROOT_PASSWORD
echo "Enter SECRET_KEY:"
read SECRET_KEY
echo "Enter TWLIGHT_OAUTH_CONSUMER_KEY:"
read TWLIGHT_OAUTH_CONSUMER_KEY
echo "Enter TWLIGHT_OAUTH_CONSUMER_SECRET:"
read TWLIGHT_OAUTH_CONSUMER_SECRET
echo "Enter TWLIGHT_EZPROXY_SECRET:"
read TWLIGHT_EZPROXY_SECRET

printf "${DJANGO_DB_NAME}" | docker secret create DJANGO_DB_NAME -
printf "${DJANGO_DB_USER}" | docker secret create DJANGO_DB_USER -
printf "${DJANGO_DB_PASSWORD}" | docker secret create DJANGO_DB_PASSWORD -
printf "${MYSQL_ROOT_PASSWORD}" | docker secret create MYSQL_ROOT_PASSWORD -
printf "${SECRET_KEY}" | docker secret create SECRET_KEY -
printf "${TWLIGHT_OAUTH_CONSUMER_KEY}" | docker secret create TWLIGHT_OAUTH_CONSUMER_KEY -
printf "${TWLIGHT_OAUTH_CONSUMER_SECRET}" | docker secret create TWLIGHT_OAUTH_CONSUMER_SECRET -
printf "${TWLIGHT_EZPROXY_SECRET}" | docker secret create TWLIGHT_EZPROXY_SECRET -

echo "Enter stack environment (eg. override \| staging \| production):"
read TWLIGHT_STACK_ENV

docker stack deploy -c "docker-compose.yml" -c "docker-compose.${TWLIGHT_STACK_ENV}.yml" "${TWLIGHT_STACK_ENV}"

echo "Setting up crontab. *WARNING* This will create duplicate jobs if run repeatedly."
(crontab -l 2>/dev/null; echo "# Run django_cron tasks.") | crontab -
(crontab -l 2>/dev/null; echo '*/5 * * * *  docker exec -t $(docker ps -q -f name="${TWLIGHT_STACK_ENV}_twlight") /app/bin/twlight_docker_entrypoint.sh python manage.py runcrons') | crontab -
(crontab -l 2>/dev/null; echo "# Update the running TWLight service if there is a new image. The initial pull is just to verify that the image is valid. Otherwise an inaccessible image could break the service.") | crontab -
(crontab -l 2>/dev/null; echo '*/5 * * * *  docker pull "wikipedialibrary/twlight:branch_${TWLIGHT_GIT_BRANCH}" >/dev/null && docker service update --image "wikipedialibrary/twlight:branch_${TWLIGHT_GIT_BRANCH}" "${TWLIGHT_STACK_ENV}_twlight"') | crontab -

EOF