from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

PASSWORD = "verysecret123"

VALID_REGISTRATION = {
    "username": "newuser",
    "email": "newuser@example.com",
    "password": PASSWORD,
    "confirmed_password": PASSWORD,
}


class AuthTestCase(APITestCase):
    """Shared setup: a known user and an empty throttle cache."""

    def setUp(self):
        # Throttle counters live in the cache and would leak between tests.
        cache.clear()
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password=PASSWORD,
        )

    def login(self):
        """Log in through the API so the client carries the JWT cookies."""
        return self.client.post(
            reverse('login'),
            {"username": "tester", "password": PASSWORD},
        )


class RegistrationTests(AuthTestCase):
    """Cover the register endpoint."""

    def test_register_creates_user(self):
        response = self.client.post(reverse('register'), VALID_REGISTRATION)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertNotIn("password", response.data)

    def test_register_rejects_mismatched_passwords(self):
        payload = {**VALID_REGISTRATION, "confirmed_password": "other"}

        response = self.client.post(reverse('register'), payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_register_requires_email(self):
        payload = {**VALID_REGISTRATION}
        del payload["email"]

        response = self.client.post(reverse('register'), payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_rejects_weak_password(self):
        payload = {
            **VALID_REGISTRATION,
            "password": "12345678",
            "confirmed_password": "12345678",
        }

        response = self.client.post(reverse('register'), payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_rejects_duplicate_username(self):
        payload = {**VALID_REGISTRATION, "username": "tester"}

        response = self.client.post(reverse('register'), payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_register_rejects_duplicate_email_case_insensitive(self):
        payload = {**VALID_REGISTRATION, "email": "Tester@Example.com"}

        response = self.client.post(reverse('register'), payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_is_throttled(self):
        for _ in range(10):
            self.client.post(reverse('register'), {})

        response = self.client.post(reverse('register'), {})

        self.assertEqual(
            response.status_code, status.HTTP_429_TOO_MANY_REQUESTS
        )


class LoginTests(AuthTestCase):
    """Cover the login endpoint and its cookies."""

    def test_login_sets_jwt_cookies(self):
        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        # the tokens themselves must not show up in the body
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertEqual(response.data["user"]["username"], "tester")

    def test_login_cookies_are_http_only_with_a_lifetime(self):
        response = self.login()

        for name in ("access_token", "refresh_token"):
            self.assertTrue(response.cookies[name]["httponly"])
            self.assertGreater(int(response.cookies[name]["max-age"]), 0)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            reverse('login'),
            {"username": "tester", "password": "wrong"},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access_token", response.cookies)

    def test_login_is_throttled(self):
        credentials = {"username": "tester", "password": "wrong"}
        for _ in range(10):
            self.client.post(reverse('login'), credentials)

        response = self.login()

        self.assertEqual(
            response.status_code, status.HTTP_429_TOO_MANY_REQUESTS
        )


class CookieAuthenticationTests(AuthTestCase):
    """Cover JWTCookieAuthentication on a protected endpoint."""

    def test_access_cookie_authenticates_request(self):
        self.login()

        response = self.client.get(reverse('quizzes'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_missing_cookie_is_rejected(self):
        response = self.client.get(reverse('quizzes'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tampered_cookie_is_rejected(self):
        self.client.cookies["access_token"] = "not-a-token"

        response = self.client.get(reverse('quizzes'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TokenRefreshTests(AuthTestCase):
    """Cover the cookie based token refresh."""

    def test_refresh_without_cookie_fails(self):
        response = self.client.post(reverse('token_refresh'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_issues_new_access_cookie(self):
        self.login()

        response = self.client.post(reverse('token_refresh'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.cookies)
        self.assertTrue(response.cookies["access_token"].value)
        self.assertNotIn("access", response.data)

    def test_refresh_with_invalid_cookie_fails(self):
        self.client.cookies["refresh_token"] = "not-a-token"

        response = self.client.post(reverse('token_refresh'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutTests(AuthTestCase):
    """Cover the logout endpoint, the blacklist and cookie removal."""

    def assert_cookies_cleared(self, response):
        for name in ("access_token", "refresh_token"):
            self.assertEqual(response.cookies[name].value, "")
            self.assertEqual(int(response.cookies[name]["max-age"]), 0)

    def test_logout_blacklists_token_and_clears_cookies(self):
        self.login()

        response = self.client.post(reverse('logout'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(BlacklistedToken.objects.count(), 1)
        self.assert_cookies_cleared(response)

    def test_logout_works_without_access_cookie(self):
        self.login()
        del self.client.cookies["access_token"]

        response = self.client.post(reverse('logout'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(BlacklistedToken.objects.count(), 1)

    def test_logout_without_refresh_cookie_fails(self):
        response = self.client.post(reverse('logout'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assert_cookies_cleared(response)

    def test_logout_rejects_blacklisted_token(self):
        self.login()
        refresh_token = self.client.cookies["refresh_token"].value
        self.client.post(reverse('logout'))
        self.client.cookies["refresh_token"] = refresh_token

        response = self.client.post(reverse('logout'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assert_cookies_cleared(response)

    def test_blacklisted_token_cannot_refresh(self):
        self.login()
        refresh_token = self.client.cookies["refresh_token"].value
        self.client.post(reverse('logout'))
        self.client.cookies["refresh_token"] = refresh_token

        response = self.client.post(reverse('token_refresh'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
