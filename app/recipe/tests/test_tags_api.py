"""
Tests for the tags API.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import Tag
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from recipe.serializers import TagSerializer


TAGS_URL = reverse("recipe:tag-list")


def detail_url(id):
    return TAGS_URL + f"{id}/"


def create_user(email="user@example.com", password="testpass123"):
    """Create and return a new user."""
    return get_user_model().objects.create_user(email, password)


class PublicTagsApiTests(TestCase):
    """Test unauthenticated API requirements."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving tags."""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test authenticated API requirements."""

    def create_tag(self, user=None, name="DefaultTag"):
        if user is None:
            user = self.user
        return Tag.objects.create(name=name, user=user)

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_list_auth_user_tags(self):
        """Test listing tags works and lists only user tags."""
        user2 = create_user(email="user2@example.com")
        self.create_tag(self.user)
        self.create_tag(self.user, "Vegan")
        self.create_tag(user2)

        res = self.client.get(TAGS_URL)
        user_tags = Tag.objects.filter(user=self.user).order_by("-name")
        serializer = TagSerializer(user_tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_update_tags_patch(self):
        """Test updating tag name with PATCH request."""
        tag = self.create_tag(name="After Dinner")
        url = detail_url(tag.id)
        payload = {"name": "Before Dinner"}
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload["name"])
        self.assertEqual(tag.user, self.user)

    def test_update_tags_put(self):
        """Test updating tag name with PUT request."""
        tag = self.create_tag(name="After Dinner")
        url = detail_url(tag.id)
        payload = {"name": "Before Dinner"}
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload["name"])
        self.assertEqual(tag.user, self.user)

    def test_delete_tags(self):
        """Test delete tag API."""
        tag = self.create_tag(name="After Dinner")
        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())
