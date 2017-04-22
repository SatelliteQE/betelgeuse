"""Sample test module."""
import unittest


def test_function():
    """Test function.

    :field1: value1
    :field2: value2
    """
    pass


class TestCase(unittest.TestCase):
    """Test case."""

    def test_method(self):
        """Test method.

        :field1: value1
        :field2: value2
        """
        pass

    def test_without_docstring(self):  # noqa: D102
        pass
