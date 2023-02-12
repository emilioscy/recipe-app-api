"""
Tests for models.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model


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
