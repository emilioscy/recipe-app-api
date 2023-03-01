"""
Test for recipe APIs.
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
    Recipe,
    Tag
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
    Ingredient
)


RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Create and return detail url."""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    """Create and return url for upload image."""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        'title': 'Sample title of recipe',
        'time_minutes': 5,
        'description': 'Sample description of recipe.',
        'price': Decimal('5.25'),
        'link': 'https://www.recipe.example.pdf'
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITest(TestCase):
    """Test unauthenticated api requests for recipe."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_is_required(self):
        """Test auth is required to call the API."""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """Test authenticated api requests for Recipe."""

    def setUp(self):
        self.user = create_user(
            email='test@example.com', password='password1234'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retriving a list of recipes."""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Test list of recipes limited to authenticatetd user."""
        other_user = create_user(
            email='test2@example.com',
            password='password1234'
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.all().filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe_id=recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating a recipe."""
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 30,
            'price': Decimal('5.99'),
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update of a recipe."""
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample title',
            link=original_link
        )

        payload = {'title': 'New title'}
        url = detail_url(recipe_id=recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, res.data['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update of recipe."""
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe',
            link='https://sample.com/recipe.pdf',
            description='Sample recipe description'
        )

        payload = {
            'title': 'Sample recipe',
            'link': 'https://sample.com/recipe.pdf',
            'description': 'Sample recipe description',
            'time_minutes': 10,
            'price': Decimal('2.50')
        }
        url = detail_url(recipe_id=recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()

        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_change_user_returns_error(self):
        """Test change recipe's user returns error."""
        new_user = create_user(
            email='example2@gmail.com',
            password='password123'
        )
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe successful."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe_error(self):
        """Test deleting other user's recipe gives error."""
        other_user = create_user(
            email='example2@gmail.com',
            password='password1234'
        )
        recipe = create_recipe(user=other_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags."""
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 10,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Tag1'}, {'name': 'Tag2'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(name=tag['name'], user=self.user)
            self.assertTrue(exists)

    def test_create_recipes_with_existing_tags(self):
        """test creating recipes with existing tags."""
        indian_tag = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 10,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Indian'}, {'name': 'Tag1'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(indian_tag, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
                ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating a tag when updating a recipe."""
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Tag1'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Tag1')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe."""
        recipe = create_recipe(user=self.user)
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe.tags.add(tag_breakfast)

        tag_launch = Tag.objects.create(user=self.user, name='Launch')
        payload = {'tags': [{'name': 'Launch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_launch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Test clearing a recipes tags."""
        tag = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def create_recipe_with_new_ingredients(self):
        """Test creating recipe with new ingredients."""
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 10,
            'price': Decimal('2.50'),
            'ingredients': [{'name': 'Ingredient1'}, {'name': 'Ingredient2'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        """Test creating recipe with existing ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Lemon')
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 10,
            'price': '2.50',
            'ingredients': [{'name': 'Lemon'}, {'name': 'Fish'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating an ingredient when updating a recipe."""
        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name': 'Ingredient1'}]}
        url = detail_url(recipe_id=recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(
            user=self.user,
            name='Ingredient1'
        )
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigning an existing ingredient when updating a recipe."""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Pepper')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name='Chili')
        payload = {'ingredients': [{'name': 'Chili'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing ingredients when updating a recipe."""
        ingredient = Ingredient.objects.create(user=self.user, name='Pepper')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_tags(self):
        """Test filtering recipes by tags."""
        recipe_1 = create_recipe(user=self.user, title='Recipe1')
        recipe_2 = create_recipe(user=self.user, title='Recipe2')
        tag_1 = Tag.objects.create(user=self.user, name='tag1')
        tag_2 = Tag.objects.create(user=self.user, name='tag1')
        recipe_1.tags.add(tag_1)
        recipe_2.tags.add(tag_2)
        recipe_3 = create_recipe(user=self.user, title='Recipe3')

        params = {'tags': f'{tag_1.id}, {tag_2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(recipe_1)
        s2 = RecipeSerializer(recipe_2)
        s3 = RecipeSerializer(recipe_3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_ingredients(self):
        """Test filtering recipes by ingredients."""
        recipe_1 = create_recipe(user=self.user, title='Recipe1')
        recipe_2 = create_recipe(user=self.user, title='Recipe2')
        ingr_1 = Ingredient.objects.create(user=self.user, name='ingr_1')
        ingr_2 = Ingredient.objects.create(user=self.user, name='ingr_2')
        recipe_1.ingredients.add(ingr_1)
        recipe_2.ingredients.add(ingr_2)
        recipe_3 = create_recipe(user=self.user, title='Recipe3')

        params = {'ingredients': f'{ingr_1.id}, {ingr_2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(recipe_1)
        s2 = RecipeSerializer(recipe_2)
        s3 = RecipeSerializer(recipe_3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    """Test upload image API."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='password1234'
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading ivalid image."""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
