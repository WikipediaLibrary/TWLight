from django.urls import re_path, path
from django.contrib.auth.decorators import login_required

from TWLight.users import views

urlpatterns = [
    path("", login_required(views.UserHomeView.as_view()), name="home"),
    re_path(
        r"^(?P<pk>\d+)/$",
        login_required(views.EditorDetailView.as_view()),
        name="editor_detail",
    ),
    re_path(
        r"^update/(?P<pk>\d+)/$",
        login_required(views.EditorUpdateView.as_view()),
        name="editor_update",
    ),
    path(
        "email_change/",
        login_required(views.EmailChangeView.as_view()),
        name="email_change",
    ),
    path("update/", login_required(views.PIIUpdateView.as_view()), name="pii_update"),
    path(
        "restrict_data/",
        login_required(views.RestrictDataView.as_view()),
        name="restrict_data",
    ),
    re_path(
        r"^delete_data/(?P<pk>\d+)/$",
        login_required(views.DeleteDataView.as_view()),
        name="delete_data",
    ),
    path(
        "my_library/",
        login_required(views.MyLibraryView.as_view()),
        name="my_library",
    ),
    re_path(
        r"^my_applications/(?P<pk>\d+)/$",
        login_required(views.ListApplicationsUserView.as_view()),
        name="my_applications",
    ),
    re_path(
        r"^return_authorization/(?P<pk>\d+)/$",
        login_required(views.AuthorizationReturnView.as_view()),
        name="return_authorization",
    ),
    # Temporary redirect from my_collection to my_library following a rename
    re_path(
        r"^my_collection/(?P<pk>\d+)/$",
        views.LibraryRedirectView.as_view(),
        name="my_collection",
    ),
    re_path(
        r"^withdraw/(?P<pk>\d+)/(?P<id>\d+)/$",
        login_required(views.WithdrawApplication.as_view()),
        name="withdraw",
    ),
    path(
        "favorite_collection/",
        login_required(views.FavoriteCollectionView.as_view()),
        name="favorite_collection",
    ),
]
