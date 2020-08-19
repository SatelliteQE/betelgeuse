# encoding=utf-8
"""Sample test module."""
import unittest


CONSTANT = 'contant-value'


def decorator(func):
    """No-op decorator."""
    return func


decorator.mark = object()


def decorator_with_args(*args, **kwargs):
    """No-op decorator that expects arguments."""
    def inner(func):
        return func
    return inner


def test_function():
    """Test function.

    :field1: value1
    :field2: value2
    """
    pass


@decorator
@decorator.mark.something
@decorator_with_args([1, b'bytes', ('a', 'b'), None])
@decorator_with_args(*[True, (True or False) and True])
@decorator_with_args((f'{CONSTANT!r:5>} with literal {{ and }}',))
@decorator_with_args({1, 2, -3})
@decorator_with_args({'a': 1, 'b': 2, **{'c': 3}})
@decorator_with_args([1, 2][0], [1, 2][:1], [1, 2][0:], [1, 2][0:1:1])
@decorator_with_args([i for i in range(5) if i % 2 == 0])
@decorator_with_args((i for i in range(5)))
@decorator_with_args({i for i in range(5)})
@decorator_with_args({k: v for k in 'abcde' for v in range(5)})
@decorator_with_args(1, 2, 3, a=1, b=2)
@decorator_with_args(
    dict(a=1, b=2),
    dict(**{'a': 1}),
    vars(decorator.mark),
    lambda a, *args, b=1, **kwargs: (a, args, b, kwargs),
    lambda a, *, b=1: (a, b),
    lambda v: v if v else None,
)
def test_decorated_test():
    """Test decorated function.

    :field1: value1
    :field2: value2
    """


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
