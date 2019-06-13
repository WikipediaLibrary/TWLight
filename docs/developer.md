# Developer docs

The intended audience for this document is future developers of TWLight. Hi!

To get set up with TWLight locally you will need [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/).

## Shell scripts

A suite of shell scripts for performing various functions can be found in the /bin folder.

Scripts starting with `virtualenv_` should be run as `www` (e.g. `sudo su www virtualenv_migrate.sh`).

### Virtual environment

To activate the Python virtual environment for the project, run:

`sudo su www`

`source /var/www/html/TWLight/bin/virtualenv_activate.sh`

### Migrating

The script `virtualenv_migrate.sh` will, for each TWLight app, run:

- `python manage.py createinitialrevisions`
- `python manage.py makemigrations`
- `python manage.py migrate`
- `python manage.py sync_translation_fields`

See the [official documentation](https://docs.djangoproject.com/en/1.11/topics/migrations/) for more on what each of these commands does.

### Testing

To test the tool, simply run the `virtualenv_test.sh` script. This script more or less only runs `python manage.py test`.

### Example data

When working on TWLight locally you may want example data reflecting the live tool. The script `virtualenv_example_data.sh` will generate 200 users, 50 resources, and 1000 applications, with pre-filled data and relations that broadly reflect the real data.

This script can only be generated with an empty database, after you have logged in to an account you want to be made a superuser (the script looks for a single account in the database and makes it a Django superuser).

## Translation

[Translations](https://github.com/wikipedialibrary/TWLight/blob/master/docs/sysadmin.md#translations) are supported in the platform. Please make sure to correctly comment new or updated strings with guidance for translators - to do so, write a comment to the line preceding the string which starts `# Translators:` in python files or `{% comment %}Translators:` in HTML.

In HTML files, make sure to wrap multiline strings with `{% blocktrans trimmed %}`, not just `{% blocktrans %}`, to avoid whitespace and indentation formatting issues.

Where possible, try to keep code and HTML tags outside of strings (i.e. `<p>{% trans "Text" %}</p>` rather than `{% trans "<p>Text</p>" %}` to avoid confusion for translators.

## Pushing changes

When filing Pull Requests for code changes, you should _not_ include translation updates and are not _required_ to include migration files. When changes are merged into the Master branch, Travis CI runs checks on the build and if it passes, pushes the changes through to the Production branch, which is then pulled to the live tool. This will run migration and string localization processes automatically.

## Specific code changes

Some bits and pieces of advice and guidance on changing specific areas of the codebase.

### Changing the data collected on application forms

Application forms are constructed at runtime, based on the requirements of the Partners that an Editor has selected. They are designed to have the minimum number of fields needed to collect that data. This means that TWLight needs to have a lot of information that it can use to construct those forms, and that information has to be consistent with itself.

Changing whether a Partner requires a particular kind of information that the system already knows about (e.g. real name) is simple and does not require developer intervention; sysadmins can set Boolean flags in the `/admin` interface.

Changing which types of information TWLight knows how to collect - e.g. if a Partner wanted to collect "job title" - is complicated, and you should read and understand this section before proceeding.

First, read the docstring in `TWLight/applications/tests.py:SynchronizeFieldsTest`.

All four places referenced there must be updated:
* Add a Boolean flag to the `Partner` model, so that Partners can indicate whether they require this data. Default it to False, as existing Partners definitionally do not require it; then `python manage.py makemigrations` .
* Add a field to either the `Application` model or the `Editor` model (optional, default blank) to allow this information to be recorded. `Editor` holds data that adhere to editors and will be the same for all of an individual's applications (like real name); `Application` holds data that is only applicable to a specific application (like a rationale for wanting access to a given resource). `python manage.py makemigrations`.
* `python manage.py migrate`.
* `applications/helpers.py`: This is where we store the data needed to construct form fields. By analogy with what's already there:
    * Create a named constant for referring to your field.
    * Add it to USER_FORM_FIELDS, PARTNER_FORM_BASE_FIELDS, or PARTNER_FORM_OPTIONAL_FIELDS, as appropriate.
    * Add an entry to FIELD_TYPES specifying the widget to be used to render the field.
    * Add an entry to FIELD_LABELS, which will be used to label the field (don't forget to wrap it in `_()`!)
    * Run the tests. `SynchronizeFieldsTest` will fail if you haven't done all the steps.

## PyCharm setup

This project can be set up via PyCharm using its support for Docker. Wikimedia developers can get free access to PyCharm Professional (required for Docker support) - please contact The Wikipedia Library for instructions.

### Process

1. After installing Docker, ensure it's using Linux Containers, and in settings, enable the 'Expose daemon on tcp://localhost:2375 without TLS' option in settings.
2. In PyCharm, open the repository folder, and navigate to Project Settings (File > Settings)
3. Under Build, Execution, Deployment > Docker, click the + symbol and check the TCP socket option is selected.
4. Navigate to Project > Project Interpreter, click the cog icon, then Add... and select the Docker Compose tab
- Configuration file(s) should be set to both `docker-compose.yml` and `docker-compose.override.yml`
- Service should be set to `twlight`.
- Set Python interpreter path to /venv/bin/python
5. It may take some time for the interpreter to finish adding. If successful, you should see a long list of python packages including Django.
6. Open the Docker tab in PyCharm's bottom bar. With the Docker entry highlighted, click the icon with three green arrows, then `Create docker-compose deployment...`
- Compose file(s) should again be set to both `docker-compose.yml` and `docker-compose.override.yml`
- Check the `--build` option
- Click Apply, then Run
7. You should see the three containers - `twlight_docker_db_1`, `twlight_docker_twlight_1`, and `twlight_docker_web_1` start up correctly.
8. Whenever you want to start the Docker containers again, you can simply click the green arrows, then 'Docker'.
