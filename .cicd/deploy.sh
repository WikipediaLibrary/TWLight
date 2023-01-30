#!/usr/bin/env bash
set -euo pipefail

branch="${1//[\/]/-}"
commit="${2}"
event_name="${3}"
gh_repo="${4}"
wikibot_token="${5}"
quaybot_username="${6:-}"
quaybot_password="${7:-}"

# Search for missing migrations and count them.
twlight_missing_migrations=$(git ls-files --others --exclude-standard 'TWLight/*/migrations/*.py' | wc -l)

# Search for new translation files and count them.
twlight_i18n_files_added=$(git ls-files --others --exclude-standard 'locale/*/LC_MESSAGES/django.po' | wc -l)

# Search for updated translation files and count them.
twlight_i18n_files_updated=$(git diff --name-only -- 'locale/*/LC_MESSAGES/django.po' | wc -l)

# Add new and updated to get change count.
twlight_i18n_files_changed=$((twlight_i18n_files_added+twlight_i18n_files_updated))

# Add remote and checkout branch
git_config() {
    echo ${FUNCNAME[0]}
    # Configure user.
    git config --global user.email "41753804+WikipediaLibraryBot@users.noreply.github.com"
    git config --global user.name "WikipediaLibraryBot"
    # Add our authenticated remote using encrypted travis environment variables.
    git remote add deploy https://WikipediaLibraryBot:${wikibot_token}@github.com/${gh_repo}.git > /dev/null 2>&1
}
# Commit migrations
git_migrate() {
    echo ${FUNCNAME[0]}
    msg="${commit} migrations"
    git add 'TWLight/*/migrations/*.py'
    git commit --message "commit ${msg}" ||:
    git fetch deploy ${branch} --quiet
    git merge --strategy recursive -X theirs deploy/${branch} --message "merge ${msg}" --quiet
}
# Commit translations
git_i18n() {
    echo ${FUNCNAME[0]}
    msg="${commit} translations"
    git add 'locale/*/LC_MESSAGES/*.po'
    git add 'locale/*/LC_MESSAGES/*.mo'
    git commit --message "commit ${msg}" ||:
    git fetch deploy ${branch} --quiet
    git merge --strategy recursive -X ours deploy/${branch} --message "merge ${msg}" --quiet
}
# Commit prod changes
git_prod() {
    echo ${FUNCNAME[0]}
    deploy_branch="${commit}-deployment"
    msg="${commit} deployment"
    git checkout -b "${deploy_branch}"
    git add -A
    git commit --message "commit ${msg}" ||:
    git fetch deploy production --quiet
    git merge --strategy ours deploy/production --message "merge ${msg}" --quiet
}
# Push built images to quay.io
docker_push() {
    echo ${FUNCNAME[0]}
    echo "$quaybot_password" | docker login quay.io -u "$quaybot_username" --password-stdin
    branch_tag="branch_${branch}"
    if [ "${branch}" = "master" ]
    then
        branch_tag="branch_production"
        docker tag "quay.io/wikipedialibrary/twlight:local" "quay.io/wikipedialibrary/twlight:${branch_tag}"
        docker tag "quay.io/wikipedialibrary/twlight_syslog:local" "quay.io/wikipedialibrary/twlight_syslog:${branch_tag}"
    fi
    declare -a repositories=("twlight" "twlight_syslog")
    for repo in "${repositories[@]}"
    do
      docker push quay.io/wikipedialibrary/${repo}:commit_${commit}
      docker push quay.io/wikipedialibrary/${repo}:${branch_tag}
    done
    docker logout quay.io
}

if [ "${event_name}" = "push" ] && [ -n "${twlight_missing_migrations:-}" ]
then
    git_config
    if [ "${twlight_i18n_files_changed}" -gt 0 ] || [ "${twlight_missing_migrations}" -gt 0 ]
    then
        # Checkout branch
        git checkout ${branch}
        # commit and merge any missing migrations
        if [ "${twlight_missing_migrations}" -gt 0 ]
        then
            git_migrate
        fi
        # commit and merge any updated translations
        if [ "${twlight_i18n_files_changed}" -gt 0 ]
        then
            git_i18n
        fi
        git push --set-upstream deploy ${branch} --quiet
        echo "pushed to ${branch}"
    elif [ "${twlight_missing_migrations}" -eq 0 ] && [ "${twlight_i18n_files_changed}" -eq 0 ]
    then
        if [ "${branch}" = "master" ] || [ "${branch}" = "staging" ]
        then
            # If no changes are needed for this commit to master, then push it to production
            if [ "${branch}" = "master" ]
            then
                git_prod
                git push --set-upstream deploy "${deploy_branch}:production" --quiet
                echo "pushed to production"
            fi
            # Push built images to quay.io
            docker_push
        fi
    fi
fi
