"""
Tests for models.
"""
from unittest.mock import patch
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models


def create_user(email, password):
    """Create and return new user."""
    return get_user_model().objects.create_user(email, password)


class ModelTests(TestCase):
    """Model testing."""

    def test_create_user_with_email_successful(self):
        """Test create user with and email is successful."""

        email = 'test@example.com'
        password = 'testpassword1234'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEquals(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """Test that email is normalized for new user."""
        sample_email = [
            ['test1@EXAMPLE.COM', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com'],
        ]
        for email, expected_email in sample_email:
            user = get_user_model().objects.create_user(
                email=email, password='test123')
            self.assertEquals(user.email, expected_email)

    def test_new_user_wothout_email_raises_error(self):
        """Test that creating new user without email raises error."""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user(
                email=None, password='test123')

    def test_create_superuser(self):
        """Test creating superuser."""
        user = get_user_model().objects.create_superuser(
            email='test1@example.com', password='test123'
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        """Test create recipe is successful."""
        user = get_user_model().objects.create_user(
            'test@example.com',
            'testpassword1234'
        )
        recipe = models.Recipe.objects.create(
            user=user,
            title='Sample recipe title.',
            time_minutes=5,
            price=Decimal('5.50'),
            description='Sample recipe description.'
        )

        self.assertEqual(str(recipe), recipe.title)

    def test_create_tag(self):
        """Test creating tag is successful."""
        user = create_user(email='example@gmail.com', password='password123')
        tag = models.Tag.objects.create(user=user, name='Tag1')

        self.assertEqual(str(tag), tag.name)

    def test_create_ingredient(self):
        """Test creating an ingredient is successful."""
        user = create_user(email='example@gmail.com', password='1234pass')
        ingredient = models.Ingredient.objects.create(
            user=user,
            name='Ingredient1'
        )

        self.assertEqual(str(ingredient), ingredient.name)

    @patch('core.models.uuid.uuid4')
    def test_recipe_file_name_uuid(self, mock_uuid):
        """Test generating image path."""
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.recipe_image_file_path(None, 'example.jpg')

        self.assertEqual(file_path, f'uploads/recipe/{uuid}.jpg')


