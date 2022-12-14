#!/usr/bin/env bash
set -euo pipefail

branch=${1}
commit=${2}
event_name=${3}
gh_repo=${4}
wikibot_token=${5}

# Search for missing migrations and count them.
twlight_missing_migrations=$(git ls-files --others --exclude-standard 'TWLight/*/migrations/*.py' | wc -l)

# Search for new translation files and count them.
twlight_i18n_files_added=$(git ls-files --others --exclude-standard 'locale/*/LC_MESSAGES/django.po' | wc -l)

# Search for updated translation files and count them.
twlight_i18n_files_updated=$(git diff --name-only -- 'locale/*/LC_MESSAGES/django.po' | wc -l)

# Add new and updated to get change count.
twlight_i18n_files_changed=$((twlight_i18n_files_added+twlight_i18n_files_updated))

# Update origin and checkout branch
git_config() {
    echo ${FUNCNAME[0]}
    # Configure user.
    git config --global user.email "41753804+WikipediaLibraryBot@users.noreply.github.com"
    git config --global user.name "WikipediaLibraryBot"
    # Remove the anonymous origin.
    git remote rm origin
    # Add our authenticated origin using encrypted travis environment variables.
    git remote add origin https://WikipediaLibraryBot:${wikibot_token}@github.com/${gh_repo}.git > /dev/null 2>&1
}
# Commit migrations
git_commit_migrations() {
    echo ${FUNCNAME[0]}
    msg="${commit} migrations"
    git add 'TWLight/*/migrations/*.py'
    # Continue even if there is nothing to commit
    git commit --message "commit ${msg}" ||:
    git fetch origin ${branch} --quiet
    git merge --strategy recursive -X theirs origin/${branch} --message "merge ${msg}" --quiet
}
# Commit translations
git_commit_i18n() {
    echo ${FUNCNAME[0]}
    msg="${commit} translations"
    git add 'locale/*/LC_MESSAGES/*.po'
    git add 'locale/*/LC_MESSAGES/*.mo'
    # Continue even if there is nothing to commit
    git commit --message "commit ${msg}" ||:
    git fetch origin ${branch} --quiet
    git merge --strategy recursive -X ours origin/${branch} --message "merge ${msg}" --quiet
}
# Commit prod changes
git_commit_prod() {
    echo ${FUNCNAME[0]}
    msg="${commit} deployment"
    git fetch origin production --quiet
    git checkout "production"
    git add -A
    # Exit if there is nothing to commit
    git commit --message "commit ${msg}" || exit 0
    git merge --strategy ours origin/production --message "merge ${msg}" --quiet
    git push origin "production" --quiet
}
# Push built images to quay.io
docker_push() {
    echo ${FUNCNAME[0]}
    declare -a repositories=("twlight" "twlight_syslog")
    for repo in "${repositories[@]}"
    do
      docker push quay.io/wikipedialibrary/${repo}:commit_${commit}
      docker push quay.io/wikipedialibrary/${repo}:branch_${branch}
    done
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
            git_commit_migrations
        fi
        # commit and merge any updated translations
        if [ "${twlight_i18n_files_changed}" -gt 0 ]
        then
            git_commit_i18n
        fi
        git push origin ${branch} --quiet
        echo "pushed to ${branch}"
    elif [ "${twlight_missing_migrations}" -eq 0 ] && [ "${twlight_i18n_files_changed}" -eq 0 ]
    then
        if [ "${branch}" = "master" ] || [ "${branch}" = "staging" ]
        then
            # If no changes are needed for this commit to master, then push it to production
            if [ "${branch}" = "master" ]
            then
                git_commit_prod
                echo "pushed to production"
            fi
            # Push built images to quay.io
            # login if we have container registry credentials
            if [ -n "${quaybot_username:-}" ] && [ -n "${quaybot_password:-}" ]
            then
                echo "$quaybot_password" | docker login quay.io -u "$cr_username" --password-stdin
                docker_push
                docker logout quay.io
            else
                docker_push
            fi
        fi
    fi
fi
