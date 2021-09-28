# Admin docs

So you want to run TWLight! Awesome. Let's get started.

These docs are written for _site administrators_ - people who have login access
to the `/admin` section of the web page and can administer user accounts and
other database objects. They are not written for 1) sysadmins; 2)
less-privileged TWLight users; or 3) developers.

In general, you will do admin-y things at the `/admin` URL. This gives you a GUI interface to the database. Good times.

## Translations

There are two types of translatable content:
1. HTML templates (and content inserted into them by Python code);
2. Objects in the database.

They use different translation procedures.

### HTML content
See `locale/README.md`. This file contains instructions for translators as well as for TWL developers working with translators. You will need a sysadmin to deploy new or updated translations.

### Database content
Objects in the database which can be translated are:
1. The Description field of Partners;
2. Tags.

Each of those objects has form fields for each supported language (e.g. description_en, description_fr). Enter whatever translations you have in the appropriate field. It is okay to leave fields blank; they will default to English. You don't have to fill in *both* the main field *and* the field for the language you're working in; they will default to the same thing. (So if your language preference is English, you can just fill in the description field and `description_en` will be set automatically; similarly, if you have the site set to French, `description_fr` will be set automatically from `description`.)

The Partner admin pages only provide the main Tag field; fill this in in English, and then use the Tag section of the admin interface to supply translations. Only fill in the name fields; the slug field will fill automatically, and you should leave the Tagged Items fields alone.

## Logging in

_If you did not create your account via OAuth_, and/or did not manually fill in accurate Wikipedia editor profile data after creating your account, you will not be able to use OAuth to log in. Instead, go to `/accounts/login`.

## Users
### Account classes
There are 3 basic classes of accounts on TWLight:
* Site administrator;
* Coordinator;
* Editor.

_Site administrators_ have superuser status, which means they can see most of the pages on the site (including everyone's editor profile pages) and they have
privileged edit access to database objects via `/admin`. You shouldn't have very many site administrators, and they should all understand that with great
(technical) power comes great (human) responsibility.

_Coordinators_ cannot log in to `/admin`, but have privileges that let them review applications. For example, they can:
* See the queue of applications to be reviewed
* See all the editor profile pages
* Set the status of applications

_Editors_ are normal users, as created via OAuth. They can:
* See their own profile page (but not anyone else's)
* See the status of all their applications (but not anyone else's)
* Apply for resource grant access

Anyone who created their account via OAuth has editor privileges by default. You can add coordinator or site administrator privileges if desired (see below).

While site administrators can create accounts via `/admin`, it is recommended to let users create them via OAuth (upgrading them to coordinator or administrator if needed), because this means that their Wikipedia user information is automatically available.

### Setting up an admin user

#### If you don't have an admin user
When sysadmins run `python manage.py syncdb` to set up the database, they are
asked if they want to set up an admin user. This is the simplest time to
establish your admin account.

If an admin account was not established at this time, then a sysadmin (or
anyone else with command-line access) can run
`python manage.py createsuperuser`.

This is the one case where you want to manually create a user, rather than going via OAuth, because OAuth-created users won't have the privileges you need to administer the site, and you need to guarantee that someone does.

#### If you do, but want another (from a new account)
If you already have a superuser, you can create another with `createsuperuser`.

Alternately, if you are a superuser (and especially if you don't have
command-line) access, do the following:
* Log in at `/admin`.
* Click '+ Add' in the Users row.
* Note that you will have to manually fill in their Wikipedia editor properties
  if desired. You don't have to fill in any of these fields; TWLight can
  create a User without an attached Editor just fine. However, some pages will
  not work properly for Users without Editors.
* Save the new user. This will allow you to edit additional properties.
* Click the superuser status checkbox and save.

#### If you want to promote an existing, OAuth-created account to superuser status
* Log in at `/admin`.
* Click on the username.
* Give them a password (there is a tiny 'this form' link in the password section).
* Set the `Staff status` checkbox to true (this allows them to log into the admin site; setting superuser status will _not_ allow that).
* Set the `Superuser status` checkbox to true.
* Save the user.
* Do _not_ change the username, but do make sure the staffer knows it, because that's what's needed for username/password authentication.

### Making someone a coordinator
When people create accounts via OAuth, they have Editor status by default. To promote them to Coordinator:
* Log into `/admin`
* Find them under the Users section
* Move _Coordinators_ from _Available groups_ to _Chosen groups_
* Click _Save_

### Deactivating & reactivating accounts

We do not *delete* accounts, because doing so would delete the application history, which we wish to retain.

We can *deactivate* accounts upon request. To do so:
* log into the `/admin`
* select one or more accounts to deactivate
* from the `Action:` dropdown, select `Deactivate selected accounts` (do NOT select the delete function) and press `Go`

This will perform the following steps:
* delete the user's email and, if known, their real name, affiliation, occupation, and country of residence
* set their account to inactive

"Inactive" means the following:
1) Users will not be able to log in.
2) You will no longer see them in your normal list of users at `/admin`.

If you want to see them in the admin site, set the `By active` filter in the sidebar to `All` or `No`.

If they want to reactivate their account, you can set the `Active` checkbox back to True and they will be permitted to log in again. We will still not have their real name, etc., although we may re-retrieve their email address from Wikipedia on login.

## Partners
Create partners via `/admin` (Partners > Add Partner), following the instructions in the form help text.

You can add one or more languages to the Language field. Use the green + to add new languages that don't appear in the list of options.

## Sending emails

Right now TWLight sends one type of email: comment notifications whenever someone comments on an application. Recipients are 1) the editor who owns that application; 2) anyone else who has commented on that application.

To make TWLight send additional emails, you (or your friendly neighborhood developer) will need to write more code. Unfortunately form emails cannot be handled through `/admin`, because database objects are not visible by default to the translation infrastructure. Storing emails as HTML in the codebase, with the `{% trans %}` or `{% blocktrans %}` tag, means they will automatically be provided to translators via Django's internationalization mechanism.

The existing `emails/tasks.py` provides a model for how additional emails can be incorporated into the codebase. The steps are:

* Write files with the text you would like to send.
    * These files should live in `emails/templates/emails/`
    * They should have the following names:
        * {your_email_type}-body-html.html
        * {your_email_type}-subject.html
        * {your_email_type}-body-text.html (optional; I have skipped it and just written a text-formatted email in the -body-html file)
    * They should `{% load i18n %}` and use `{% trans %}` or `{% blocktrans %}` to mark text for translation.
    * They are Django templates, so you can supply them with context which will be rendered in the usual manner.
* Define a TemplateMail subclass in `emails/tasks.py` which has a line `name = {your_email_type}`.
* Define a function in `emails/tasks.py` which sends the email. (See the `email =` and `email.send()` lines in `emails/tasks.py` for examples of 1) instantiating a class of your template mail; 2) sending it.)
* Identify where you want to trigger email sending.
* At that point, you have two options:
    * call the function you just defined (this is in general easier and more debuggable, and you should do it unless you can't)
    * send a signal, and make sure the function you defined is a `@receiver` of that signal (may be necessary if third-party apps, like `django.contrib.comments`, are your trigger)
