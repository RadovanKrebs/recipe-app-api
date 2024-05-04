"""
Tests for the user API.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token


CREATE_USER_URL = reverse("user:create")
CREATE_TOKEN_URL = reverse("user:token")
ME_URL = reverse("user:me")


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """Test the public features of user API."""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test creating a user is successful"""
        payload = {
            "email": "test@example.com",
            "password": "pass123",
            "name": "Test Name",
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEquals(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", res.data)

    def test_user_with_email_exists_error(self):
        """Test error returned if user with email exists."""
        payload = {
            "email": "test@example.com",
            "password": "pass123",
            "name": "Test Name",
        }
        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEquals(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        payload = {
            "email": "test@example.com",
            "password": "pw",
            "name": "Test Name",
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEquals(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = (
            get_user_model()
            .objects.filter(
                email=payload["email"],
            )
            .exists()
        )
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test generates token for valid credentials."""
        user_details = {
            "name": "Test Name",
            "email": "test@example.com",
            "password": "pass123",
        }
        user = create_user(**user_details)

        user_details.pop("name")
        res = self.client.post(CREATE_TOKEN_URL, user_details)

        self.assertIn("token", res.data)
        self.assertEquals(res.status_code, status.HTTP_200_OK)
        Token.objects.get(user=user)

    def test_create_token_bad_email(self):
        """Test generate token fails for invalid credentials."""
        user_details = {
            "name": "Test Name",
            "email": "test@example.com",
            "password": "pass123",
        }
        user = create_user(**user_details)

        invalid_credentials1 = {
            "email": "wrong_test@example.com",
            "password": "pass123",
        }

        res = self.client.post(CREATE_TOKEN_URL, invalid_credentials1)

        self.assertNotIn("token", res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_create_token_bad_password(self):
        """Test generate token fails for invalid credentials."""
        user_details = {
            "name": "Test Name",
            "email": "test@example.com",
            "password": "pass123",
        }
        user = create_user(**user_details)

        invalid_credentials2 = {
            "email": "test@example.com",
            "password": "wrong_pass123",
        }

        res = self.client.post(CREATE_TOKEN_URL, invalid_credentials2)

        self.assertNotIn("token", res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_retrieve_user_unauthorized(self):
        """Test authentication is required for users."""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    class PrivateUserApiTests(TestCase):
        """Test user API requests that require authentication."""

        def setUP(self):
            self.user = create_user(
                email="test@example.com",
                password="pass123",
                name="Test Name",
            )
            self.client = APIClient()
            self.client.force_authenticate(user=self.user)

        def test_retrieve_profile_success(self):
            """Test retrieving profile for logged in user."""
            res = self.client.get(ME_URL)

            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(
                res.data,
                {
                    "name": self.user.name,
                    "email": self.user.email,
                },
            )

        def test_post_me_not_allowed(self):
            """Test that post requests are not accepted."""
            res = self.client.post(ME_URL, {})

            self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        def test_update_user_profile(self):
            """Test updating the user profile for the authenticated user."""
            payload = {"name": "Updated name", "password": "newpass123"}

            res = self.client.patch(ME_URL, payload)

            self.user.refresh_from_db()
            self.assertEqual(self.user.name, payload["name"])
            self.assertTrue(self.user.check_password(payload["password"]))
            self.assertEqual(res.status_code, status.HTTP_200_OK)
