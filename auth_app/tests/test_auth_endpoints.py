from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class RegistrationTests(APITestCase):
    """Cover the register endpoint."""

    def test_register_creates_user(self):
        response = self.client.post(
            reverse('register'),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "verysecret123",
                "confirmed_password": "verysecret123",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse('register'),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "verysecret123",
                "confirmed_password": "something_else",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="newuser").exists())


class LoginTests(APITestCase):
    """Cover the login endpoint and its cookies."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="verysecret123",
        )

    def test_login_sets_jwt_cookies(self):
        response = self.client.post(
            reverse('login'),
            {"username": "tester", "password": "verysecret123"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        # the tokens themselves must not show up in the body
        self.assertNotIn("access", response.data)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            reverse('login'),
            {"username": "tester", "password": "wrong"},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access_token", response.cookies)


class TokenRefreshTests(APITestCase):
    """Cover the cookie based token refresh."""

    def test_refresh_without_cookie_fails(self):
        response = self.client.post(reverse('token_refresh'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
