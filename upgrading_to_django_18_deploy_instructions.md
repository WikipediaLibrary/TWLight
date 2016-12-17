Upgrading to Django!
* put everything on a testing server
    * git pull whatever the current thing on prod is 
    * install whatever dependencies are on prod
* make sure the SECURE_HSTS_SECONDS setting didn't break anything
    * remove or increase it accordingly
* Go through below procedure, minus part about warning users
    * update it as needed

* warn users about downtime
* stop gunicorn
* uninstall system django so we don't accidentally use it
* workon TWLight
* pip install -r requirements.txt
    * make sure www-data ends up as owner of virtualenv
* python manage.py migrate django_comments --fake-initial
* python manage.py migrate
* python manage.py collectedstatic
* restart gunicorn