"""
Tests for recipe APIs.
"""

from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Ingredient,
    Recipe,
    Tag,
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)


RECIPES_URL = reverse("recipe:recipe-list")


def detail_url(id):
    """Create a recipe detail URL"""
    return reverse("recipe:recipe-list") + f"{id}/"


def image_upload_url(recipe_id):
    """Create and return image upload url."""
    return reverse("recipe:recipe-upload-image", args=[recipe_id])


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
        Tag.objects.create(name="Asian", user=self.user)
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

    def test_recipe_create_tag_on_update(self):
        """Test creating a new tag when updating a recipe."""
        recipe = create_recipe(self.user)
        tag_name = "Chicken"

        payload = {
            "tags": [
                {"name": tag_name},
            ],
        }

        res = self.client.patch(detail_url(recipe.id), payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(name=tag_name)
        self.assertEqual(recipe.tags.count(), len(payload["tags"]))
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe."""
        old_tag = Tag.objects.create(user=self.user, name="Lunch")
        recipe = create_recipe(self.user)
        recipe.tags.add(old_tag)

        existing_tag = Tag.objects.create(user=self.user, name="Breakfast")
        payload = {
            "tags": [
                {"name": existing_tag.name},
            ],
        }

        res = self.client.patch(detail_url(recipe.id), payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(existing_tag, recipe.tags.all())
        self.assertEqual(Tag.objects.filter(name=existing_tag.name).count(), 1)
        self.assertNotIn(old_tag, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Test removing all tags from recipe."""
        old_tag = Tag.objects.create(user=self.user, name="Lunch")
        recipe = create_recipe(self.user)
        recipe.tags.add(old_tag)

        payload = {
            "tags": [],
        }

        res = self.client.patch(detail_url(recipe.id), payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.all().count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Test creating recipe with new ingredients."""
        payload = {
            "title": "Chicken Katsu 2",
            "time_minutes": 10,
            "price": Decimal("7.10"),
            "ingredients": [
                {"name": "Chicken"},
                {"name": "Rice"},
            ],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(title=payload["title"])
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingr in payload["ingredients"]:
            exists = recipe.ingredients.filter(
                name=ingr["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_new_and_old_ingredients(self):
        """Test creating recipe with new ingredients."""
        old_ingr = Ingredient.objects.create(name="Chicken", user=self.user)
        payload = {
            "title": "Chicken Katsu 2",
            "time_minutes": 10,
            "price": Decimal("7.10"),
            "ingredients": [
                {"name": "Chicken"},
                {"name": "Rice"},
            ],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(title=payload["title"])
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertTrue(
            Ingredient.objects.filter(
                id=old_ingr.id,
                name=old_ingr.name,
            ).exists()
        )

        for ingr in payload["ingredients"]:
            exists = recipe.ingredients.filter(
                name=ingr["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredients_on_recipe_update(self):
        """Test creating new ingredients when updating recipe."""
        recipe = create_recipe(self.user)
        payload = {
            "ingredients": [
                {"name": "Chicken"},
                {"name": "Rice"},
            ],
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertEqual(len(ingredients), 2)
        recipe.refresh_from_db()
        for ingr in payload["ingredients"]:
            exists = recipe.ingredients.filter(
                name=ingr["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_assign_ingredients_on_recipe_update(self):
        """Test assigning existing new ingredients when updating recipe."""
        existing_ingredient = Ingredient.objects.create(user=self.user, name="Lemon")
        recipe = create_recipe(self.user)
        payload = {
            "ingredients": [
                {"name": "Lemon"},
            ],
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertEqual(len(ingredients), 1)
        recipe.refresh_from_db()
        self.assertTrue(recipe.ingredients.filter(id=existing_ingredient.id))

    def test_clearing_recipe_ingredients(self):
        """Test clearing recipe ingredients."""
        ingredient = Ingredient.objects.create(user=self.user, name="Pork")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {
            "ingredients": [],
        }

        url = detail_url(recipe.id)

        res = self.client.patch(url, payload, format="json")

        recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)


class ImageUploadTests(TestCase):
    """Tests for the image upload API."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test upload an image to a recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)
            payload = {"image": image_file}
            res = self.client.post(url, payload, format="multipart")

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading invalid image."""
        url = image_upload_url(self.recipe.id)
        payload = {"image": "notanimage"}
        res = self.client.post(url, payload, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
