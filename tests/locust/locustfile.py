from html.parser import HTMLParser
import json
from os import environ
import re
from urllib.parse import urlparse
from locust import HttpUser, task

wpUsers = json.loads(environ.get("WPUSERS"))
reCsrfMiddlewareToken = re.compile(
    r'<input type="hidden" name="csrfmiddlewaretoken" value="([0-9a-zA-Z]+)">',
)
reWpLoginToken = re.compile(
    r'<input name="wpLoginToken" type="hidden" value="([^"+\\]+\+\\)"/>',
)
reMyApplicationsUrl = re.compile(
    r"<a href='(/users/my_applications/\d+/)'>My Applications</a>",
)


class MyCollectionsAccessParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        self.hrefs = []
        self.href = None
        super().__init__()

    def return_data(self):
        return self.hrefs

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for i, attr in enumerate(attrs):
                prev_attr = None
                if 0 <= i - 1 < len(attrs):
                    prev_attr = attrs[i - 1]
                if (
                    attr[0] == "class"
                    and attr[1] == "btn btn-sm access-apply-button"
                    and prev_attr
                    and prev_attr[0] == "href"
                ):
                    self.href = prev_attr[1]

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.hrefs.append(self.href)
            self.href = None


class MyAppsWithdrawParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        self.forms = []
        self.form = {}
        super().__init__()

    def return_data(self):
        return self.forms

    def handle_starttag(self, tag, attrs):
        if tag == "form":
            self.form = {
                "action": None,
                "csrfmiddlewaretoken": None,
                "submit": None,
            }
            for attr in attrs:
                if attr[0] == "action":
                    self.form["action"] = attr[1]

        if (
            tag == "input"
            and self.form
            and "action" in self.form
            and self.form["action"] is not None
        ):
            for i, attr in enumerate(attrs):
                next_attr = None
                if 0 <= i + 1 < len(attrs):
                    next_attr = attrs[i + 1]
                if (
                    attr[0] == "name"
                    and attr[1] == "csrfmiddlewaretoken"
                    and next_attr
                    and next_attr[0] == "value"
                ):
                    self.form["csrfmiddlewaretoken"] = next_attr[1]
                if (
                    attr[0] == "type"
                    and attr[1] == "submit"
                    and next_attr
                    and next_attr[0] == "value"
                    and next_attr[1] == "Withdraw"
                ):
                    self.form["submit"] = next_attr[1]

    def handle_endtag(self, tag):
        if tag == "form":
            self.forms.append(self.form)
            self.form = {}


class LoggedInUser(HttpUser):
    def on_start(self):
        self.user = {}
        self.login()

    def on_stop(self):
        self.logout()

    def login(self):
        self.user = wpUsers.pop(0)
        if self.user and self.user["wpName"] and self.user["wpPassword"]:
            name = "/oauth/login/?next=/users/my_library/"
            with self.client.get(
                name,
                name=name,
                catch_response=True,
                stream=True,
            ) as get_login:
                if any(
                    (match := reWpLoginToken.search(line))
                    for line in get_login.iter_lines(decode_unicode=True)
                ):
                    wp_login_token = match.group(1)
                    if wp_login_token:
                        post_data = {
                            "wpName": self.user["wpName"],
                            "wpPassword": self.user["wpPassword"],
                            "wploginattempt": "Log+in",
                            "wpEditToken": "+\\",
                            "title": "Special:UserLogin",
                            "authAction": "login",
                            "force": "",
                            "wpLoginToken": wp_login_token,
                        }
                        url = urlparse(get_login.url)
                        name = str(url.scheme) + "://" + str(url.netloc) + str(url.path)
                        with self.client.post(
                            get_login.url,
                            post_data,
                            name=name,
                            catch_response=True,
                            stream=True,
                        ) as post_login:
                            if "sessionid" not in self.client.cookies:
                                post_login.failure("login failed: No sessionid")
                            if post_login.status_code != 200:
                                post_login.failure(
                                    "post_login status code: "
                                    + str(post_login.status_code)
                                )
        else:
            raise Exception("login failed: credentials required.")

    def logout(self):
        self.client.get(
            "/accounts/logout/?next=/",
        )
        if self.user["wpName"] and self.user["wpPassword"]:
            wpUsers.append(self.user)
            self.user = {}

    @task(10)
    def get_my_library(self):
        name = "/users/my_library/"
        with self.client.get(
            name,
            name=name,
            catch_response=True,
            stream=True,
        ) as get_my_library:
            if get_my_library.status_code != 200:
                get_my_library.failure(
                    "get_my_library status code: " + str(get_my_library.status_code)
                )

            my_collections_parser = MyCollectionsAccessParser()
            for line in get_my_library.iter_lines(decode_unicode=True):
                my_collections_parser.feed(line)
            hrefs = my_collections_parser.return_data()
            for href in hrefs:
                with self.client.get(
                    href, name=href, catch_response=True, stream=True
                ) as get_collection_content:
                    if get_collection_content.status_code >= 400:
                        get_collection_content.failure(
                            href
                            + " failed with status code: "
                            + str(get_collection_content.status_code)
                        )
                    url = urlparse(get_collection_content.url)
                    this_host = str(url.scheme) + "://" + str(url.netloc)
                    if this_host == self.host:
                        get_collection_content.failure("unexpected host: " + this_host)
                    # We're streaming the response to generate traffic to the access url while minimizing memory usage
                    if get_collection_content:
                        for line in get_collection_content.iter_lines(
                            decode_unicode=True
                        ):
                            pass

    @task(10)
    def get_users(self):
        self.client.get(
            "/users/",
        )

    @task(10)
    def get_partners(self):
        self.client.get(
            "/partners/",
        )

    @task(1)
    def post_applications(self):
        name = "/applications/request/"
        with self.client.get(
            name,
            name=name,
            allow_redirects=False,
            catch_response=True,
            stream=True,
        ) as get_app_req:
            if get_app_req.status_code != 200:
                get_app_req.failure(
                    "get_app_req status code: " + str(get_app_req.status_code)
                )
            url = urlparse(get_app_req.url)
            this_host = str(url.scheme) + "://" + str(url.netloc)
            if this_host != self.host:
                get_app_req.failure("unexpected host: " + this_host)
            if any(
                (match := reCsrfMiddlewareToken.search(line))
                for line in get_app_req.iter_lines(decode_unicode=True)
            ):
                csrf_middleware_token = match.group(1)
                if csrf_middleware_token:
                    with self.client.post(
                        get_app_req.url,
                        {
                            "csrfmiddlewaretoken": csrf_middleware_token,
                            "partner_24": "on",
                            "partner_49": "on",
                            "partner_60": "on",
                            "partner_62": "on",
                            "partner_102": "on",
                            "partner_11": "on",
                            "partner_47": "on",
                            "partner_73": "on",
                            "partner_63": "on",
                            "partner_31": "on",
                            "partner_58": "on",
                            "partner_79": "on",
                            "partner_15": "on",
                            "partner_74": "on",
                            "partner_71": "on",
                            "partner_9": "on",
                            "partner_56": "on",
                            "partner_44": "on",
                            "partner_43": "on",
                            "partner_22": "on",
                            "partner_68": "on",
                            "partner_77": "on",
                            "partner_72": "on",
                            "partner_18": "on",
                            "partner_41": "on",
                            "partner_80": "on",
                            "partner_16": "on",
                            "partner_112": "on",
                            "partner_40": "on",
                            "partner_53": "on",
                            "partner_111": "on",
                            "partner_27": "on",
                            "partner_26": "on",
                            "partner_81": "on",
                            "partner_17": "on",
                            "partner_39": "on",
                            "partner_38": "on",
                            "partner_110": "on",
                            "partner_100": "on",
                            "partner_37": "on",
                            "partner_69": "on",
                            "partner_30": "on",
                            "partner_20": "on",
                            "partner_21": "on",
                            "partner_50": "on",
                            "partner_67": "on",
                            "partner_108": "on",
                            "partner_103": "on",
                            "partner_10": "on",
                            "partner_70": "on",
                            "partner_12": "on",
                            "partner_76": "on",
                            "partner_19": "on",
                            "partner_83": "on",
                        },
                        name=url.path,
                        catch_response=True,
                        stream=True,
                    ) as post_app_req:
                        if post_app_req.status_code != 200:
                            post_app_req.failure(
                                "post_app_req status code: "
                                + str(post_app_req.status_code)
                            )
                            url = urlparse(post_app_req.url)
                            this_host = str(url.scheme) + "://" + str(url.netloc)
                            if this_host != self.host:
                                post_app_req.failure("unexpected host: " + this_host)
                        with self.client.post(
                            post_app_req.url,
                            {
                                "csrfmiddlewaretoken": csrf_middleware_token,
                                "real_name": "Test",
                                "affiliation": "Test",
                                "partner_24_rationale": "Test",
                                "partner_24_comments": "Test",
                                "partner_49_rationale": "Test",
                                "partner_49_comments": "Test",
                                "partner_60_requested_access_duration": "1",
                                "partner_60_rationale": "Test",
                                "partner_60_comments": "Test",
                                "partner_62_requested_access_duration": "1",
                                "partner_62_rationale": "Test",
                                "partner_62_comments": "Test",
                                "partner_102_agreement_with_terms_of_use": "on",
                                "partner_102_rationale": "Test",
                                "partner_102_comments": "Test",
                                "partner_11_rationale": "Test",
                                "partner_11_comments": "Test",
                                "partner_47_rationale": "Test",
                                "partner_47_comments": "Test",
                                "partner_73_rationale": "Test",
                                "partner_73_comments": "Test",
                                "partner_63_requested_access_duration": "1",
                                "partner_63_rationale": "Test",
                                "partner_63_comments": "Test",
                                "partner_31_requested_access_duration": "1",
                                "partner_31_rationale": "Test",
                                "partner_31_comments": "Test",
                                "partner_58_requested_access_duration": "1",
                                "partner_58_rationale": "Test",
                                "partner_58_comments": "Test",
                                "partner_79_rationale": "Test",
                                "partner_79_comments": "Test",
                                "partner_15_rationale": "Test",
                                "partner_15_comments": "Test",
                                "partner_74_rationale": "Test",
                                "partner_74_comments": "Test",
                                "partner_71_rationale": "Test",
                                "partner_71_comments": "Test",
                                "partner_9_requested_access_duration": "1",
                                "partner_9_rationale": "Test",
                                "partner_9_comments": "Test",
                                "partner_56_rationale": "Test",
                                "partner_56_comments": "Test",
                                "partner_44_requested_access_duration": "1",
                                "partner_44_rationale": "Test",
                                "partner_44_comments": "Test",
                                "partner_43_requested_access_duration": "1",
                                "partner_43_rationale": "Test",
                                "partner_43_comments": "Test",
                                "partner_22_specific_stream": "17",
                                "partner_22_requested_access_duration": "1",
                                "partner_22_rationale": "Test",
                                "partner_22_comments": "Test",
                                "partner_68_rationale": "Test",
                                "partner_68_comments": "Test",
                                "partner_77_requested_access_duration": "1",
                                "partner_77_rationale": "Test",
                                "partner_77_comments": "Test",
                                "partner_72_specific_title": "Test",
                                "partner_72_rationale": "Test",
                                "partner_72_comments": "Test",
                                "partner_18_rationale": "Test",
                                "partner_18_comments": "Test",
                                "partner_41_requested_access_duration": "1",
                                "partner_41_rationale": "Test",
                                "partner_41_comments": "Test",
                                "partner_80_specific_title": "Test",
                                "partner_80_rationale": "Test",
                                "partner_80_comments": "Test",
                                "partner_16_specific_title": "Test",
                                "partner_16_rationale": "Test",
                                "partner_16_comments": "Test",
                                "partner_112_rationale": "Test",
                                "partner_112_comments": "Test",
                                "partner_40_rationale": "Test",
                                "partner_40_comments": "Test",
                                "partner_53_requested_access_duration": "1",
                                "partner_53_rationale": "Test",
                                "partner_53_comments": "Test",
                                "partner_111_rationale": "Test",
                                "partner_111_comments": "Test",
                                "partner_27_rationale": "Test",
                                "partner_27_comments": "Test",
                                "partner_26_account_email": "test@example.com",
                                "partner_26_rationale": "Test",
                                "partner_26_comments": "Test",
                                "partner_81_rationale": "Test",
                                "partner_81_comments": "Test",
                                "partner_17_requested_access_duration": "1",
                                "partner_17_rationale": "Test",
                                "partner_17_comments": "Test",
                                "partner_39_rationale": "Test",
                                "partner_39_comments": "Test",
                                "partner_38_requested_access_duration": "1",
                                "partner_38_rationale": "Test",
                                "partner_38_comments": "Test",
                                "partner_110_rationale": "Test",
                                "partner_110_comments": "Test",
                                "partner_100_specific_stream": "31",
                                "partner_100_requested_access_duration": "1",
                                "partner_100_rationale": "Test",
                                "partner_100_comments": "Test",
                                "partner_37_rationale": "Test",
                                "partner_37_comments": "Test",
                                "partner_69_requested_access_duration": "1",
                                "partner_69_rationale": "Test",
                                "partner_69_comments": "Test",
                                "partner_30_rationale": "Test",
                                "partner_30_comments": "Test",
                                "partner_20_requested_access_duration": "1",
                                "partner_20_rationale": "Test",
                                "partner_20_comments": "Test",
                                "partner_21_requested_access_duration": "1",
                                "partner_21_rationale": "Test",
                                "partner_21_comments": "Test",
                                "partner_50_rationale": "Test",
                                "partner_50_comments": "Test",
                                "partner_67_specific_stream": "28",
                                "partner_67_requested_access_duration": "1",
                                "partner_67_rationale": "Test",
                                "partner_67_comments": "Test",
                                "partner_108_rationale": "Test",
                                "partner_108_comments": "Test",
                                "partner_103_account_email": "test@example.com",
                                "partner_103_rationale": "Test",
                                "partner_103_comments": "Test",
                                "partner_10_requested_access_duration": "1",
                                "partner_10_rationale": "Test",
                                "partner_10_comments": "Test",
                                "partner_70_rationale": "Test",
                                "partner_70_comments": "Test",
                                "partner_12_rationale": "Test",
                                "partner_12_comments": "Test",
                                "partner_76_rationale": "Test",
                                "partner_76_comments": "Test",
                                "partner_19_rationale": "Test",
                                "partner_19_comments": "Test",
                                "partner_83_rationale": "Test",
                                "partner_83_comments": "Test",
                                "submit": "Apply",
                            },
                            name=url.path,
                            catch_response=True,
                            stream=True,
                        ) as post_app_apply:
                            if post_app_apply.status_code != 200:
                                post_app_apply.failure(
                                    "post_app_apply status code: "
                                    + str(post_app_apply.status_code)
                                )
                            this_host = url.scheme + "://" + url.netloc
                            if this_host != self.host:
                                post_app_apply.failure("unexpected host: " + this_host)
                            if "messages" in self.client.cookies:
                                match = reMyApplicationsUrl.search(
                                    self.client.cookies["messages"]
                                )
                                if match:
                                    path = match.group(1)
                                    if path:
                                        with self.client.get(
                                            path,
                                            name="/users/my_applications/<user>/",
                                            catch_response=True,
                                            stream=True,
                                        ) as get_my_apps:
                                            my_apps_parser = MyAppsWithdrawParser()
                                            for line in get_my_apps.iter_lines(
                                                decode_unicode=True
                                            ):
                                                my_apps_parser.feed(line)
                                            forms = my_apps_parser.return_data()
                                            for form in forms:
                                                with self.client.post(
                                                    form["action"],
                                                    {
                                                        "csrfmiddlewaretoken": form[
                                                            "csrfmiddlewaretoken"
                                                        ],
                                                        "submit": form["submit"],
                                                    },
                                                    name="/users/withdraw/<user>/<app>/",
                                                    catch_response=True,
                                                ) as post_withdraw_app:
                                                    if (
                                                        post_withdraw_app.status_code
                                                        >= 400
                                                    ):
                                                        post_withdraw_app.failure(
                                                            "post_withdraw_app status code: "
                                                            + str(
                                                                post_withdraw_app.status_code
                                                            )
                                                        )
                                                    url = urlparse(
                                                        post_withdraw_app.url
                                                    )
                                                    this_host = (
                                                        str(url.scheme)
                                                        + "://"
                                                        + str(url.netloc)
                                                    )
                                                    if this_host != self.host:
                                                        post_withdraw_app.failure(
                                                            "unexpected host: "
                                                            + this_host
                                                        )
