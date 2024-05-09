"""
Tests for recipe APIs.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Tag,
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
    TagSerializer,
)


RECIPES_URL = reverse("recipe:recipe-list")


def detail_url(id):
    """Create a recipe detail URL"""
    return reverse("recipe:recipe-list") + f"{id}/"


def create_recipe(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        "title": "Sample recipe title",
        "time_minutes": 22,
        "description": "Default description.",
        "price": Decimal("5.25"),
        "link": "https://example.com/recipe.pdf",
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """Tests unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """Tests authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email="user@example.com", password="passwd123", name="User Name"
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes."""
        for _ in range(3):
            create_recipe(self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by("-id")
        serilizer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serilizer.data)

    def test_recipe_list_limited_to_user(self):
        """Test that other user's recipes not returned."""
        new_user = create_user(
            email="user2@example.com", password="passwd123", name="User Name2"
        )

        create_recipe(new_user)
        create_recipe(self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user).order_by("-id")
        serilizer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serilizer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail"""
        create_recipe(self.user)
        recipe2 = create_recipe(self.user)

        url = detail_url(recipe2.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe2)
        self.assertTrue(serializer.data, res.data)

    def test_create_recipe(self):
        """Test creating a recipe"""
        payload = {
            "title": "Unique title",
            "time_minutes": 22,
            "description": "Default description.",
            "price": Decimal("5.25"),
            "link": "https://example.com/recipe.pdf",
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data["id"])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test patrial update on a recipe."""
        original_link = "https://exapmle.com/recipe.pdf"
        recipe = create_recipe(
            user=self.user,
            title="Sample recipe",
            link=original_link,
        )

        payload = {"title": "New title."}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload["title"])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update on a recipe."""
        original_link = "https://exapmle.com/recipe.pdf"
        recipe = create_recipe(
            user=self.user,
            title="Sample recipe",
            link=original_link,
            description="ORG desc.",
        )

        payload = {
            "title": "Edit",
            "time_minutes": 69,
            "description": "Edited description.",
            "price": Decimal("5.69"),
            "link": "https://example.com/edit/recipe.pdf",
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_user_update_has_no_effect(self):
        """Test changing the recipe user does not work."""
        new_user = create_user(email="userrr@example.com", password="passwd122")
        recipe = create_recipe(user=self.user)

        payload = {"user": new_user}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deletiong recipe works."""
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        self.client.delete(url)

        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_cant_delete_other_user_recipe(self):
        """Test if you can't delete other user's recipes"""
        new_user = create_user(email="userrr@example.com", password="passwd122")
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertTrue(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags."""
        payload = {
            "title": "Chicken Katsu",
            "time_minutes": 10,
            "price": Decimal("7.10"),
            "tags": [
                {"name": "Japanese"},
                {"name": "Asian"},
            ],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(title=payload["title"])
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload["tags"]:
            exists = recipe.tags.filter(
                name=tag["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_new_and_existing_tags(self):
        """Test creating a recipe with new and existing tags."""
        existing_tag = Tag.objects.create(name="Asian", user=self.user)
        payload = {
            "title": "Chicken Katsu",
            "time_minutes": 10,
            "price": Decimal("7.10"),
            "tags": [
                {"name": "Japanese"},
                {"name": "Asian"},
            ],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(title=payload["title"])
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]

        self.assertEqual(Tag.objects.filter(user=self.user).count(), 2)
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload["tags"]:
            exists = recipe.tags.filter(
                name=tag["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)
