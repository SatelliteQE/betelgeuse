"""Tests for :mod:`betelgeuse.source_generator`."""
from betelgeuse import collector


def test_source_generator():
    """Check if ``collect_tests`` 'tests/data'collect tests."""
    tests = collector.collect_tests('tests/data/test_sample.py')
    test_decorated_test = [
        test for test in tests['tests/data/test_sample.py']
        if test.name == 'test_decorated_test'
    ].pop()

    assert test_decorated_test.decorators == [
        'decorator',
        'decorator.mark.something',
        "decorator_with_args([1, b'bytes', ('a', 'b'), None])",
        'decorator_with_args(*[True, ((True or False) and True)])',
        "decorator_with_args((f'{CONSTANT!r:5>} with literal {{ and }}',))",
        'decorator_with_args({1, 2, (- 3)})',
        "decorator_with_args({'a': 1, 'b': 2, **{'c': 3}})",

        'decorator_with_args([1, 2][0], [1, 2][:1], [1, 2][0:], '
        '[1, 2][0:1:1])',

        'decorator_with_args([i for i in range(5) if ((i % 2) == 0)])',
        'decorator_with_args((i for i in range(5)))',
        'decorator_with_args({i for i in range(5)})',
        "decorator_with_args({k: v for k in 'abcde' for v in range(5)})",
        'decorator_with_args(1, 2, 3, a=1, b=2)',

        'decorator_with_args('
        'dict(a=1, b=2), '
        "dict(**{'a': 1}), "
        'vars(decorator.mark), '
        '(lambda a, *args, b=1, **kwargs: (a, args, b, kwargs)), '
        '(lambda a, *, b=1: (a, b)), '
        '(lambda v: (v if v else None))'
        ')',
    ]
