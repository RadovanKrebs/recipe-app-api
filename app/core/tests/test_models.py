"""
Tests for models.
"""

from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models


def create_user(email="user@example.com", password="testpass123"):
    """Create and return a new user."""
    return get_user_model().objects.create_user(email, password)


class ModelTests(TestCase):
    """Test models."""

    # User tests

    def test_create_user_with_email_successful(self):
        """Tests creating a user with an email successful."""
        email = "test@example.com"
        password = "testpass123"
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

        self.assertEquals(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """Test email is normalized for new users."""
        sample_emails = [
            ["test1@EXAMPLE.com", "test1@example.com"],
            ["Test2@Example.com", "Test2@example.com"],
            ["TEST3@EXAMPLE.COM", "TEST3@example.com"],
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, "passwd123")
            self.assertEquals(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """Tests that creating a user without email raises an error."""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user("", "pass123")

    def test_new_user_invalid_email_validation(self):
        """Tests that creating a user without email raises an error."""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user("sda", "pass123")

        with self.assertRaises(ValueError):
            get_user_model().objects.create_user("sda@a", "pass123")

        get_user_model().objects.create_user("sda@a.com", "pass123")

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = get_user_model().objects.create_superuser(
            "test@example.com",
            "pass123",
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    # Recipe tests

    def test_create_recipe(self):
        """Test creating a recipe success."""
        email = "test@example.com"
        password = "testpass123"
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

        recipe = models.Recipe.objects.create(
            title="Test recipe",
            user=user,
            time_minutes=5,
            price=Decimal("5.50"),
            description="Sample desc.",
        )

        self.assertEqual(str(recipe), recipe.title)

    def test_create_tag(self):
        """Test crating a tag is successful."""
        user = create_user()
        tag = models.Tag.objects.create(user=user, name="Tag1")

        self.assertEqual(str(tag), tag.name)
