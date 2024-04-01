from django.urls import re_path
from django.contrib.auth.decorators import login_required

from TWLight.applications import views
from TWLight.users.models import Editor
from TWLight.resources.models import Partner

urlpatterns = [
    re_path(
        r"editor/autocomplete/",
        views.EditorAutocompleteView.as_view(model=Editor),
        name="editor_autocomplete",
    ),
    re_path(
        r"^partner/autocomplete/$",
        views.PartnerAutocompleteView.as_view(model=Partner),
        name="partner_autocomplete",
    ),
    re_path(
        r"^apply/(?P<pk>\d+)/$",
        login_required(views.SubmitSingleApplicationView.as_view()),
        name="apply_single",
    ),
    re_path(
        r"^evaluate/(?P<pk>\d+)/$",
        login_required(views.EvaluateApplicationView.as_view()),
        name="evaluate",
    ),
    re_path(
        r"^list/$", login_required(views.ListApplicationsView.as_view()), name="list"
    ),
    re_path(
        r"^list/approved/$",
        login_required(views.ListApprovedApplicationsView.as_view()),
        name="list_approved",
    ),
    re_path(
        r"^list/rejected/$",
        login_required(views.ListRejectedApplicationsView.as_view()),
        name="list_rejected",
    ),
    re_path(
        r"^list/expiring/$",
        login_required(views.ListRenewalApplicationsView.as_view()),
        name="list_renewal",
    ),
    re_path(
        r"^list/sent/$",
        login_required(views.ListSentApplicationsView.as_view()),
        name="list_sent",
    ),
    re_path(
        r"^send/$",
        login_required(views.ListReadyApplicationsView.as_view()),
        name="send",
    ),
    re_path(
        r"^send/(?P<pk>\d+)/$",
        login_required(views.SendReadyApplicationsView.as_view()),
        name="send_partner",
    ),
    re_path(
        r"^batch_edit/$",
        login_required(views.BatchEditView.as_view()),
        name="batch_edit",
    ),
    re_path(
        r"^renew/(?P<pk>\d+)/$",
        login_required(views.RenewApplicationView.as_view()),
        name="renew",
    ),
]
