# README
This is where Django will look for translation files, according to
https://docs.djangoproject.com/en/1.7/topics/i18n/translation/#how-django-discovers-translations .

See https://docs.djangoproject.com/en/1.7/topics/i18n/translation/#localization-how-to-create-language-files for full instructions on creating language files.

## Translation process

Run these commands from the root `TWLight/` directory.

1.`python manage.py makemessages -l <language_code> -e py,html` (make a file for a new language); and/or
2. `python manage.py makemessages -a` (updates existing files)
3. Send the .po files to your translator(s) and have them fill in translation strings.
4. `django-admin.py compilemessages` (compiles .po files processed by your translators into .mo files usable by the computer)

## Troubleshooting
### Having trouble setting things up?

The `locale/ `directory must be manually created (but it has been, so this should not be a problem).

To make your translation files, you need to run `django-admin.py makemessages -l <language_code> --pythonpath=</path/to/your/project> -e py,html` (not manage.py, apparently).

If you're working on a virtualenv, deactivate it so django-admin can find gettext.

You can manage your gettext installation with homebrew, if you have it. If django-admin claims your version isn't high enough but brew thinks it is, `brew link --force gettext` to tell the system to use the brew version.

### Getting errors like `/path/to/django.po:439:18: invalid multibyte sequence`?

The encoding on your file has gone awry.

Check your encoding:
`file -I path/to/django.po`

Output will look something like `path/to/django.po: text/plain; charset=iso-8859-1`.

Change your encoding to utf-8: `iconv -f iso-8859-1 -t utf-8 path/to/django.po `

The from setting should match what `file` told you about the file encoding.

### Getting errors about whitespace (like `msgid` and `msgstr` do not both begin or end with `\n`)?

You can fix them manually. You can also improve your code to make them less likely to recur:
* Use `blocktrans trimmed`, not just `blocktrans`
* Format multiline strings in .py files in ways that do not have leading or terminating newlines

You should also ensure your translators know that they need to preserve whitespace (including whitespace-only lines), and that `\n` is a whitespace character.
