from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from TWLight.applications import views
from TWLight.users.models import Editor
from TWLight.resources.models import Partner

urlpatterns = [
    url(
        r"^editor/autocomplete/$",
        views.EditorAutocompleteView.as_view(model=Editor),
        name="editor_autocomplete",
    ),
    url(
        r"^partner/autocomplete/$",
        views.PartnerAutocompleteView.as_view(model=Partner),
        name="partner_autocomplete",
    ),
    url(
        r"^apply/(?P<pk>\d+)/$",
        login_required(views.SubmitSingleApplicationView.as_view()),
        name="apply_single",
    ),
    url(
        r"^evaluate/(?P<pk>\d+)/$",
        login_required(views.EvaluateApplicationView.as_view()),
        name="evaluate",
    ),
    url(r"^list/$", login_required(views.ListApplicationsView.as_view()), name="list"),
    url(
        r"^list/approved/$",
        login_required(views.ListApprovedApplicationsView.as_view()),
        name="list_approved",
    ),
    url(
        r"^list/rejected/$",
        login_required(views.ListRejectedApplicationsView.as_view()),
        name="list_rejected",
    ),
    url(
        r"^list/expiring/$",
        login_required(views.ListRenewalApplicationsView.as_view()),
        name="list_renewal",
    ),
    url(
        r"^list/sent/$",
        login_required(views.ListSentApplicationsView.as_view()),
        name="list_sent",
    ),
    url(
        r"^send/$",
        login_required(views.ListReadyApplicationsView.as_view()),
        name="send",
    ),
    url(
        r"^send/(?P<pk>\d+)/$",
        login_required(views.SendReadyApplicationsView.as_view()),
        name="send_partner",
    ),
    url(
        r"^batch_edit/$",
        login_required(views.BatchEditView.as_view()),
        name="batch_edit",
    ),
    url(
        r"^renew/(?P<pk>\d+)/$",
        login_required(views.RenewApplicationView.as_view()),
        name="renew",
    ),
]
