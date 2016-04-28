# Admin docs

So you want to run TWLight! Awesome. Let's get started.

These docs are written for _site administrators_ - people who have login access
to the /admin section of the web page and can administer user accounts and
other database objects. They are not written for 1) sysadmins or 2)
less-privileged TWLight users.

In general, you will do admin-y things at the `/admin` URL. This gives you a GUI interface to the database. Good times.

## Logging in

_If you did not create your account via OAuth_ and did not manually fill in accurate Wikipedia editor profile data after creating your account, you will not be able to use OAuth to log in. Instead, go to `/accounts/login`.

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

#### If you do, but want another
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

### Making someone a coordinator
When people create accounts via OAuth, they have Editor status by default. To promote them to Coordinator:
* Log into `/admin`
* Find them under the Users section
* Move _Coordinators_ from _Available groups_ to _Chosen groups_
* Click _Save_

## Partners
https://django-durationfield.readthedocs.org/en/latest/#usage
TODO

## Sending emails

Right now TWLight sends one type of email: comment notifications whenever someone comments on an application. Recipients are 1) the editor who owns that application; 2) anyone else who has commented on that application.

To make TWLight send additional emails, you (or your friendly neighborhood developer) will need to write more code. Unfortunately form emails cannot be handled through `/admin`, because database objects are not visible to the translation infrastructure. Storing emails as HTML in the codebase, with the `{% trans %}` or `{% blocktrans %}` tag, means they will automatically be provided to translators via Django's internationalization mechanism.

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