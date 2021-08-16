from os import environ
import re
from locust import HttpUser, task

wpName = environ.get("WPNAME")
wpPassword = environ.get("WPPASSWORD")
reCsrfMiddlewareToken = re.compile(
    r'<input type="hidden" name="csrfmiddlewaretoken" value="([0-9a-zA-Z]+)">',
    re.DOTALL,
)
reWpLoginToken = re.compile(
    r'<input name="wpLoginToken" type="hidden" value="([^"+\\]+\+\\)"/>', re.DOTALL
)


class LoggedInUser(HttpUser):
    def on_start(self):
        self.login()

    def on_stop(self):
        self.logout()

    def login(self):
        if wpName and wpPassword:
            get_login = self.client.get(
                "/oauth/login/?next=/home/",
                catch_response=True,
            )
            match = reWpLoginToken.search(get_login.text)

            wpLoginToken = None
            if match:
                wpLoginToken = match.group(1)
                post_data = {
                    "wpName": wpName,
                    "wpPassword": wpPassword,
                    "wploginattempt": "Log+in",
                    "wpEditToken": "+\\",
                    "title": "Special:UserLogin",
                    "authAction": "login",
                    "force": "",
                    "wpLoginToken": wpLoginToken,
                }
                post_login = self.client.post(
                    get_login.url,
                    post_data,
                    catch_response=True,
                )
                if "cookie" not in post_login.cookies:
                    print("login failed: No cookies")
                    post_login.failure("login failed: No cookies")
                if post_login.status_code != 200:
                    print("login failed: status code " + str(post_login.status_code))
                    print(self.client.cookies)
                    post_login.failure(
                        "login failed: status code " + str(post_login.status_code)
                    )
        else:
            raise Exception("login failed: credentials required.")

    def logout(self):
        self.client.get(
            "/accounts/logout/?next=/",
        )

    @task(1)
    def get_my_library(self):
        get_my_library = self.client.get(
            "/users/my_library/",
        )

    @task(1)
    def get_users(self):
        self.client.get(
            "/users/",
        )

    @task(1)
    def get_partners(self):
        self.client.get(
            "/partners/",
        )

    @task(1)
    def post_applications(self):
        get_app_req = self.client.get(
            "/applications/request/",
            allow_redirects=False,
            #            catch_response=True,
        )
        #        if get_app_req.status_code != 200:
        #            get_app_req.failure('Redirected to login page')
        # print(get_app_req.url)
        # print(get_app_req.status_code)
        # print(get_app_req.headers)
        # print(self.client.cookies)
        # print(get_app_req.cookies)
        # csrfMiddlewareToken = response.cookies['csrfMiddlewareToken']
        match = reCsrfMiddlewareToken.search(get_app_req.text)
        if match:
            csrfMiddlewareToken = match.group(1)
            if csrfMiddlewareToken:
                # print(csrfMiddlewareToken)
                # print(get_app_req.url)
                post_app_req = self.client.post(
                    "/applications/request/",
                    {
                        "csrfmiddlewaretoken": csrfMiddlewareToken,
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
                    # cookies = self.client.cookies,
                    catch_response=True,
                    # headers = {"Content-Type": "application/x-www-form-urlencoded"},
                )
                # print(post_app_req.text)

                # def post_applications_apply(self):
                # get_apps_apply = self.client.get("/applications/apply/")
                post_apps_apply = self.client.post(
                    "/applications/apply/",
                    {
                        "csrfmiddlewaretoken": csrfMiddlewareToken,
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
                    catch_response=True,
                )
