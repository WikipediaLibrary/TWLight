# Developer docs

The intended audience for this document is developers of TWLight. Hi!

To get set up with TWLight locally you will need [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/).

We are in the process of consolidating and structuring our documentation in [the Wiki](https://github.com/WikipediaLibrary/TWLight/wiki), please look there!

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
