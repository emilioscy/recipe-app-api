"""Sample tests"""

from django.test import SimpleTestCase

from app import calc


class CalcTests(SimpleTestCase):
    """Tests for calc module"""

    def test_addition(self):
        """Test addition"""
        res = calc.add(3, 0)

        self.assertEqual(res, 3)

    def test_substraction(self):
        """Test substraction"""
        res = calc.substract(6, 3)

        self.assertEqual(res, 3)
