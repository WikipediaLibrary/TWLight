Upgrading to Django!
* warn users about downtime
* stop gunicorn
* workon TWLight
* pip install -r requirements.txt
    * make sure www-data ends up as owner of virtualenv
* python manage.py migrate django_comments --fake-initial
* python manage.py migrate
* python manage.py collectedstatic
* restart gunicorn