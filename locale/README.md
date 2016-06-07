# README
This is where Django will look for translation files, according to
https://docs.djangoproject.com/en/1.7/topics/i18n/translation/#how-django-discovers-translations .

See https://docs.djangoproject.com/en/1.7/topics/i18n/translation/#localization-how-to-create-language-files for full instructions on creating language files.

## Translation process

Run these commands from the root `TWLight/` directory.

1.`django-admin.py makemessages -l <language_code> --pythonpath=</path/to/your/project> -e py,html` (make a file for a new language); and/or
2. `django-admin.py makemessages -a` (updates existing files)
3. Send the .po files to your translator(s) and have them fill in translation strings.
4. `django-admin.py compilemessages` (compiles .po files processed by your translators into .mo files usable by the computer)

## Troubleshooting
Having trouble setting things up?

The `locale/ `directory must be manually created (but it has been, so this should not be a problem).

To make your translation files, you need to run `django-admin.py makemessages -l <language_code> --pythonpath=</path/to/your/project> -e py,html` (not manage.py, apparently).

If you're working on a virtualenv, deactivate it so django-admin can find gettext.

You can manage your gettext installation with homebrew, if you have it. If django-admin claims your version isn't high enough but brew thinks it is, `brew link --force gettext` to tell the system to use the brew version.