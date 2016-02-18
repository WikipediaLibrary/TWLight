from django.test import TestCase

# Create your tests here.

"""
totally test that resources.models.Partner, applications.models.Application,
and applications.helpers are in sync.
"""

"""
# Request for Application
Requires: nothing
Produces (on GET): dynamic form with a boolean for each available Resource
            can I cache this??
Produces (on valid POST): Application object and FKed Optional Applications
Produces (on invalid POST): back to the dynamic form, though I dunno how you'd
            manage invalidity there
needs to be restricted to logged-in users - is in urls.py - but are you using
decorators or mixins for that? if this is a mixins-heavy app, make it a mixin.

# Application
Requires: an Application (may have FKed optional applications)
Produces: a completed application

form_valid must include special validation; since the application must be
produced in an incomplete state by the previous view, we need to have a way to
clean it separately here. Also we need to have a property and/or model manager
that search only fully validated applications.

Should be restricted *to the relevant user*, not just login_required.

Some fields need to be displayed only once; some must be displayed once per
requesting partner.

# Application queue
listview of fully validated applications with some sort of status indicators,
probably filterable by status

# Application evaluation
lalala can assign statuses and version things and there are responsible parties,
deal with this later
"""

"""
Desired behavior...

Users go to a screen where they select the resources they would like to apply
for. This should be a form constructed on the fly from all resources in the
system. (Which means we need to set another flag for making them available or
not.)

Submitting this creates a _request for application_ - a list of entities they
want to apply for. I don't think we need to actually persist this data past the
session?

I think if I'm going to do this in a relatively transparent and maintainable
way, I'm going to end up hardcoding the same optional-field information in
several places. And if I'm going to do THAT, I need to test it. So test that the
following cover the same fields:
* some authoritative source of truth about optional fields
* the list of optional fields available on Resource
* the list of optional fields available in OptionalApplication

RfA may actually be a stub application - just boolean values on all the 
resources. But ugh, I actually want to generate that dynamically from available
resources. So no. I think on form valid, an RfA generates an Application which
I can then persist.

What about caching the RfA form so we don't need to make it every time? And
quite frankly the subforms only need to be regenerated when their FKed objects
change. Hm.

django-material relies too heavily on JS; noscript will break the UI. Wonder how
much I can harvest from them or google for forms without JS.

users need to be able to see their own application status
"""