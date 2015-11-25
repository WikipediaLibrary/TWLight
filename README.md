# README.md

* Set up a postgres database matching the parameters in the DATABASES setting. (Yes, it must be postgres.)
* `pip install -r requirements.txt`
* Set the following environment variables:
    - `DJANGO_DEBUG` (must be `False` on production, can be `True` for testing)
    - `DJANGO_SECRET_KEY`
    - `DJANGO_SETTINGS_MODULE`