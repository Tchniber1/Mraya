import json
from unittest import mock

from django.test import override_settings

from apps.core.testing import MrayaTestCase


class AuthTests(MrayaTestCase):
    def test_pages_require_login(self):
        for url in ("/", "/dashboard/"):
            response = self.client.get(url)
            self.assertRedirects(response, "/accounts/login/", fetch_redirect_response=False)

    def test_json_api_returns_401(self):
        response = self.client.post("/dashboard/products/x/status/", data="{}",
                                    content_type="application/json", HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 401)

    def test_login_page_renders(self):
        response = self.client.get("/accounts/login/")
        self.assertContains(response, "Mr")
        self.assertContains(response, "Try the demo account")

    @override_settings(MRAYA_DEV_LOGIN=True)
    def test_dev_login_flow(self):
        response = self.client.post("/accounts/dev-login/")
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.repo.get_user("demo-user")["display_name"], "Demo User")

    @override_settings(MRAYA_DEV_LOGIN=False)
    def test_dev_login_disabled(self):
        self.assertEqual(self.client.post("/accounts/dev-login/").status_code, 404)

    def test_firebase_session_valid_token(self):
        claims = {"uid": "g-123", "email": "x@gmail.com", "name": "X Y", "picture": ""}
        with mock.patch("apps.accounts.firebase.verify_id_token", return_value=claims):
            response = self.client.post("/accounts/session/", data=json.dumps({"idToken": "tok"}),
                                        content_type="application/json")
        self.assertEqual(response.json(), {"redirect": "/"})
        self.assertEqual(self.repo.get_user("g-123")["email"], "x@gmail.com")

    def test_firebase_session_redirects_returning_user_to_dashboard(self):
        self.repo.save_user("g-123", {"has_analysis": True})
        with mock.patch("apps.accounts.firebase.verify_id_token", return_value={"uid": "g-123"}):
            response = self.client.post("/accounts/session/", data=json.dumps({"idToken": "tok"}),
                                        content_type="application/json")
        self.assertEqual(response.json(), {"redirect": "/dashboard/"})

    def test_firebase_session_rejects_bad_tokens(self):
        response = self.client.post("/accounts/session/", data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        with mock.patch("apps.accounts.firebase.verify_id_token", side_effect=ValueError("bad")):
            response = self.client.post("/accounts/session/", data=json.dumps({"idToken": "t"}),
                                        content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_logout(self):
        self.sign_in()
        self.client.post("/accounts/logout/")
        self.assertEqual(self.client.get("/").status_code, 302)
