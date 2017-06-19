# README
This is where Django will look for translation files, according to
https://docs.djangoproject.com/en/1.7/topics/i18n/translation/#how-django-discovers-translations .

See https://docs.djangoproject.com/en/1.7/topics/i18n/translation/#localization-how-to-create-language-files for full instructions on creating language files. See https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html for documentation of the `.po` format.

## Translation process (for translators)

Translators: what you'll see is a lot of things that look like this:

```
#: TWLight/applications/forms.py:101
msgid "Apply"
msgstr ""
```

The first line is the place in the codebase where you can find the translation string; if this is useful to you, the code lives at https://github.com/thatandromeda/TWLight/ ; feel free to ignore this information if it is not useful to you.

The msgid is the original English; please leave this alone.

Fill in the quotation marks in msgstr with the target language.

Please do this in a *text editor* and not a word processor, if those are meaningful terms to you; if they're not, don't worry, just edit with whatever tools you like and save it as text format. Please also preserve the line breaks and the number of quotation marks, if possible.

Some sections have comments, which are prefaced with `Translators:`, like this:

```
#. Translators: This labels a section of a form where we ask users to enter info (like country of residence) when applying for resource access.
#: TWLight/applications/forms.py:188
msgid "About you"
msgstr ""
```

These are intended to explain or disambiguate things which need context to be clear. Please leave the translator comments alone, but I hope they are useful. Please tell the developer if there are other ambiguous things that need to be commented.

Finally, some sections have variables, like this:

```
#: TWLight/applications/forms.py:201
#, python-brace-format
msgid "Your application to {partner}"
msgstr ""
```

Anything between curly braces is a variable, which will be filled in at run time. (In this case, `partner` is the name of a publishing partner - I've tried to use descriptive variable names.) Put this variable (including the curly braces) wherever it needs to go in the translation (but *do* include it, and *don't* translate the part between the curly braces). So, e.g., 

`msgstr "lörëm {partner} ÿpsüm"`

Some places the variable syntax is instead `%(variablename)s` - again, just move that chunk around unchanged wherever it needs to go. (The `s` is not a typo and should not be changed.)

There are a few places where two versions of the translation string are provided, plural and singular, and you will need to provide multiple translations accordingly. (If the target language needs more than two singular/plural forms, talk to the developer.)

Use non-gendered language where possible. If not possible, use neutral gender terms as available. If not possible, use both forms separated by a slash, as in Latina/o or Latina/Latino. (TWL's English is written to avoid use of gendered terms, but the Wikipedia Library recognizes that this is not possible in all languages.) 

If this is not the first time a translation has been made in your target language, you may see lines that start with `#| msgid` rather than `msgid`. These lines indicate the English text that the site had whenever the last translation file was generated (`#| msgid`), so that you can compare it to the current version (`msgid`) and see whether updates are needed. You will also see the previous translation, if available, following `msgstr`. You are welcome to leave it alone if it's still correct.

## Translation process (for sysadmins)

Run these commands from the root `TWLight/` directory.

1.`python manage.py makemessages -l <language_code> -e py,html` (make a file for a new language); and/or
2. `python manage.py makemessages -a` (update existing files)
3. Send the .po files to your translator(s) and have them fill in translation strings.
4. `python manage.py compilemessages` (compile .po files processed by your translators into .mo files usable by the computer)

When you deploy a new language:
* Add it to the `LANGUAGES` variable in `TWLight/settings/base.py`.
    * It's OK to do this after you get the file from the translator; Django has suitable built-in translations of language names. IN fact, it's considerate to wait until after getting the translation file, because users may be frustrated if they choose a language and the site cannot display in that language.
* Run `python manage.py makemigrations` and `python manage.py migrate`.
    * Translatable database fields will need to add an additional field for the new language.
    * You need to do this *on the server* as well as on localhost; the migrations for the translated fields in django-taggit are outside of your codebase's version control since it's a dependency, so the new migrations will not automatically come into being on the server when you deploy the code.

The contents of the `LANGUAGES` variable will automatically be offered to users as options for site translation on their user profile pages. If they choose a language that doesn't yet have a translation file available, the site will render in the default language specified by LANGUAGE_CODE. (Users may not be able to read this, but the app will not crash.) If the translation file is incomplete, translation strings will be rendered in their original language (probably English).

## Troubleshooting (for sysadmins)
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

You can fix them manually. You can also improve the code to make them less likely to recur:
* Use `{% blocktrans trimmed %}` in templates, not just `{% blocktrans %}`
* Format multiline strings in `.py` files in ways that do not have leading or terminating newlines

You should also ensure your translators know that they need to preserve whitespace (including whitespace-only lines); that `\n` is a newline character; that they DO have to preserve any `\n`s at the beginning and end of the string; that they DON'T have to preserve any of the others - they can use them if the spirit of the original expects carriage returns, but they don't have to.

### `CommandError: The /path/to/django.po file has a BOM (Byte Order Mark). Django only supports .po files encoded in UTF-8 and without any BOM.` ?

Remove the BOM. Techniques vary. See, e.g., https://stackoverflow.com/questions/1068650/using-awk-to-remove-the-byte-order-mark (command line) or http://blog.toshredsyousay.com/post/27543408832/how-to-add-or-remove-a-byte-order-mark (Sublime Text).

### "keyword $foo unknown" errors?
Make sure that any quotation marks inside of your msgstrs are escaped (`\"`, not `"`).

### Syntax errors pertaining to a multiline string?

Your multiline strings should be formatted thus:

```""
"substring 1"
"substring 2, which has a newline at the end\n"
"substring 3"
""
```

Note the double quotes at the beginning and end, the single quotes around each string, and the `\n` newline character where needed.