# Admin docs

So you want to run TWLight! Awesome. Let's get started.

These docs are written for _site administrators_ - people who have login access
to the `/admin` section of the web page and can administer user accounts and
other database objects. They are not written for 1) sysadmins; 2)
less-privileged TWLight users; or 3) developers.

In general, you will do admin-y things at the `/admin` URL. This gives you a GUI interface to the database. Good times.

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
* See the queue of applications to be reviewed for the partner(s) they are assigned to
* See some editor profile pages
* Set the status of applications to partner(s) they are assigned to

Coordinators should not be able to interact with users or applications for partners to which they are not assigned.

_Editors_ are normal users, as created via OAuth. They can:
* See their own profile page (but not anyone else's)
* See the status of all their applications (but not anyone else's)
* Apply for resource grant access

Anyone who created their account via OAuth has editor privileges by default. You can add coordinator or site administrator privileges if desired (see below).

While site administrators can create accounts via `/admin`, it is recommended to let users create them via OAuth (upgrading them to coordinator or administrator if needed), because this means that their Wikipedia user information is automatically available.

### Setting up an admin user

#### If you don't have an admin user
A sysadmin (or anyone else with command-line access) can run
`python manage.py createsuperuser` to create an admin if there are currently no existing admins.

This is the one case where you want to manually create a user, rather than going via OAuth, because OAuth-created users won't have the privileges you need to administer the site, and you need to guarantee that someone does.

#### If you do, but want another (from a new account)
If you already have a superuser, you can create another with `createsuperuser`.

Alternately, if you are a superuser (and especially if you don't have
command-line access), do the following:
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

We can *deactivate* (rather than fully delete) accounts upon request. To do so:
* log into the `/admin`
* select one or more accounts to deactivate
* from the `Action:` dropdown, select `Deactivate selected accounts` (not the delete function) and press `Go`

This will perform the following steps:
* delete the user's email and, if known, their real name, affiliation, occupation, and country of residence
* set their account to inactive

"Inactive" means the following:
1) Users will not be able to log in.
2) You will no longer see them in your normal list of users at `/admin`.

If you want to see them in the admin site, set the `By active` filter in the sidebar to `All` or `No`.

If they want to reactivate their account, you can set the `Active` checkbox back to True and they will be permitted to log in again. We will still not have their real name, etc., although we may re-retrieve their email address from Wikipedia on login.

Users can delete their own account (fully deleting it, not just deactivating) via their own user page.

## Partners
Create partners via `/admin` (Partners > Add Partner), following the instructions in the form help text.

You can add one or more languages to the Language field. Use the green + to add new languages that don't appear in the list of options.

### Collections

In order to set up a collection (database, stream, etc.) for a partner:
* Log in at `/admin`
* Under `Resources`, click on `Collections`
* Click the `Add collection +` button

The existing partners are available in the dropdown. You can also add a new partner with the green + sign by the dropdown.
