from django.test import TestCase

# Test views
# EditorDetailView resolves at URL
# Smoke test for editor data
# Editor can see own info
# Editor cannot see someone else's info
# Coordinator can see someone else's info
# Site admin can see someone else's info

# Does django-braces give me a like can-see-own mixin? can I decorate that?

# Test user creation
# receiving signal from oauth results in creation of editor model
# receiving signal from oauth results in creation of coordinator model
# coordinator status is false
# site admin status is false
# editor model contains all expected info (mock out the signal)
