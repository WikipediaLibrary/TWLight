from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from TWLight.users import views

urlpatterns = [
    url(r'^$', 
       login_required(views.UserHomeView.as_view()),
        name='home'),
    url(r'^(?P<pk>\d+)/$',
       login_required(views.EditorDetailView.as_view()),
        name='editor_detail'),
    url(r'^update/(?P<pk>\d+)/$',
       login_required(views.EditorUpdateView.as_view()),
        name='editor_update'),
    url(r'^email_change/$',
       login_required(views.EmailChangeView.as_view()),
        name='email_change'),
    url(r'^update/$',
       login_required(views.PIIUpdateView.as_view()),
        name='pii_update'),
    url(r'^restrict_data/$',
       login_required(views.RestrictDataView.as_view()),
        name='restrict_data'),
    url(r'^delete_data/(?P<pk>\d+)/$',
       login_required(views.DeleteDataView.as_view()),
        name='delete_data'),
    url(r'^my_collection/(?P<pk>\d+)/$',
        login_required(views.ListApplicationsUserView.as_view()),
        name='my_collection'),
]
