from django.conf.urls import url

from TWLight.users import views

urlpatterns = [
    url(r'^$', 
        views.UserHomeView.as_view(),
        name='home'),
    url(r'^(?P<pk>\d+)/$',
        views.EditorDetailView.as_view(),
        name='editor_detail'),
    url(r'^update/(?P<pk>\d+)/$',
        views.EditorUpdateView.as_view(),
        name='editor_update'),
    url(r'^email_change/$',
        views.EmailChangeView.as_view(),
        name='email_change'),
    url(r'^update/$',
        views.PIIUpdateView.as_view(),
        name='pii_update'),
]
