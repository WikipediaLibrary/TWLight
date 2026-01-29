#!/usr/bin/env bash
# Installs dependencies and deploys TWLight to a single Debian host.

# Uninstall any conflicting packages
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc
do
    apt remove $pkg
done

# Add Docker's official GPG key:
apt update
apt install ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update

# Install docker
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Install other packages we require
apt install -y cron

# Cleanup unneeded packages
apt autoremove -y

# Add twlight user
adduser twlight --disabled-password --quiet --gecos "" ||:
usermod -a -G docker twlight

# Delete any existing repo
rm -rf /srv/TWLight
# Pull TWLight code and make twlight user the owner
git clone https://github.com/WikipediaLibrary/TWLight.git /srv/TWLight
cd /srv/TWLight || exit
# Get on correct branch
echo "Enter git branch:"
read -r TWLIGHT_GIT_BRANCH
git checkout "${TWLIGHT_GIT_BRANCH}" && git pull

# Get input from human
echo "Enter DJANGO_DB_NAME:"
read -r DJANGO_DB_NAME
echo "Enter DJANGO_DB_USER:"
read -r DJANGO_DB_USER
echo "Enter TWLIGHT_OAUTH_CONSUMER_KEY:"
read -r TWLIGHT_OAUTH_CONSUMER_KEY
echo "Enter TWLIGHT_OAUTH_CONSUMER_SECRET:"
read -r TWLIGHT_OAUTH_CONSUMER_SECRET
echo "Enter TWLIGHT_EZPROXY_SECRET:"
read -r TWLIGHT_EZPROXY_SECRET
echo "Enter MW_API_EMAIL_USER"
read -r MW_API_EMAIL_USER
echo "Enter MW_API_EMAIL_PASSWORD"
read -r MW_API_EMAIL_PASSWORD
echo "Enter stack environment (eg. override | staging | production):"
read -r TWLIGHT_STACK_ENV

# Setup DKIM
ssh-keygen -t rsa -b 1024 -m PEM -P "" -f dkim
ssh-keygen -f dkim.pub -m PKCS8 -e > dkim.pub.pkcs8
DKIM_PRIVATE_KEY=$(cat dkim)
DKIM_DNS_TXT=$(tail -n +2 dkim.pub.pkcs8 | head -n -1 | tr -d '\n')
rm dkim dkim.pub dkim.pub.pkcs8

# Generate some secrets
DJANGO_DB_PASSWORD=$(openssl rand -hex 30)
MYSQL_ROOT_PASSWORD=$(openssl rand -hex 30)
SECRET_KEY=$(openssl rand -hex 50)

# Deploy TWLight
chown -R twlight:twlight /srv/TWLight
read -r -d '' TWLIGHT <<- EOF
echo "Initialising swarm"
docker swarm init
echo "Deleting any existing services"
docker service ls -q | xargs docker service rm ||:
echo "Deleting any existing secrets"
docker secret ls -q | xargs docker secret rm ||:

cd /srv/TWLight

echo "Creating secrets"
printf "${DJANGO_DB_NAME}" | docker secret create DJANGO_DB_NAME -
printf "${DJANGO_DB_USER}" | docker secret create DJANGO_DB_USER -
printf "${DJANGO_DB_PASSWORD}" | docker secret create DJANGO_DB_PASSWORD -
printf "'''${DKIM_PRIVATE_KEY}'''" | docker secret create DKIM_PRIVATE_KEY -
printf "${MYSQL_ROOT_PASSWORD}" | docker secret create MYSQL_ROOT_PASSWORD -
printf "${SECRET_KEY}" | docker secret create SECRET_KEY -
printf "${TWLIGHT_OAUTH_CONSUMER_KEY}" | docker secret create TWLIGHT_OAUTH_CONSUMER_KEY -
printf "${TWLIGHT_OAUTH_CONSUMER_SECRET}" | docker secret create TWLIGHT_OAUTH_CONSUMER_SECRET -
printf "${TWLIGHT_EZPROXY_SECRET}" | docker secret create TWLIGHT_EZPROXY_SECRET -
printf "${MW_API_EMAIL_USER}" | docker secret create MW_API_EMAIL_USER -
printf "${MW_API_EMAIL_PASSWORD}" | docker secret create MW_API_EMAIL_PASSWORD -
echo "Deploying stack"
docker stack deploy -c "docker-compose.yml" -c "docker-compose.${TWLIGHT_STACK_ENV}.yml" "${TWLIGHT_STACK_ENV}"
echo "Setting up crontab. *WARNING* This will create duplicate jobs if run repeatedly."
(crontab -l 2>/dev/null; echo "# Run django_cron tasks.") | crontab -
(crontab -l 2>/dev/null; echo '*/5 * * * *  docker exec -t \$(docker ps -q -f name=${TWLIGHT_STACK_ENV}_twlight) /app/bin/twlight_docker_entrypoint.sh python manage.py runcrons') | crontab -
(crontab -l 2>/dev/null; echo "# Update the running TWLight service if there is a new image. The initial pull is just to verify that the image is valid. Otherwise an inaccessible image could break the service.") | crontab -
(crontab -l 2>/dev/null; echo '*/5 * * * *  /srv/TWLight/bin/./twlight_docker_deploy.sh ${TWLIGHT_STACK_ENV} branch_${TWLIGHT_GIT_BRANCH}') | crontab -
(crontab -l 2>/dev/null; echo "# Reclaim disk space previously used by docker.") | crontab -
(crontab -l 2>/dev/null; echo '*/30 * * * * docker system prune -a -f; docker volume rm \$(docker volume ls -qf dangling=true)') | crontab -
EOF

sudo su --login twlight /usr/bin/env bash -c "${TWLIGHT}"

echo "NOTE: YOU MUST CREATE THE FOLLOWING DNS ENTRY FOR EMAIL TO WORK:"
echo " name                               | type | record "
echo " ${TWLIGHT_STACK_ENV}._domainkey.twl.wmflabs.org. | TXT | \"v=DKIM1;t=s;p=${DKIM_DNS_TXT}\" "
