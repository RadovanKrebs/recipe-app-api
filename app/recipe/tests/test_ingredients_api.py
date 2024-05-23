"""
Tests for the ingredients API.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse("recipe:ingredient-list")


def detail_url(id):
    return INGREDIENTS_URL + f"{id}/"


def create_user(email="user@example.com", password="testpass123"):
    """Create and return a new user."""
    return get_user_model().objects.create_user(email, password)


def create_ingredient(user, name="Def Ing"):
    return Ingredient.objects.create(user=user, name=name)


class PublicIngredientsApiTests(TestCase):
    """Test the unauthenticated ingredients API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that auth is required."""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test the authenticated ingredients API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_list_ingredients(self):
        """Test the list ingredients endpoint."""
        create_ingredient(self.user, name="A")
        create_ingredient(self.user, name="B")

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredients = Ingredient.objects.filter(user=self.user).order_by("-name")
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_limited_to_user(self):
        """Test ingredients are limited to authenticated user."""
        ing = create_ingredient(self.user, name="Kale")
        new_user = create_user(email="new@example.com")
        create_ingredient(new_user, name="Chocolate")

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], ing.name)
        self.assertEqual(res.data[0]["id"], ing.id)

    def test_update_ingredient(self):
        """Test updating an ingredient."""
        ingredient = create_ingredient(self.user)

        url = detail_url(ingredient.id)
        new_name = "Bay Leaf"
        payload = {"name": new_name}

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload["name"])

    def test_delete_ingredient(self):
        """Test deleting an ingredient"""
        ingredient = create_ingredient(self.user)

        url = detail_url(ingredient.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.all()
        self.assertEqual(len(ingredients), 0)
