"""Tests for :mod:`betelgeuse.source_generator`."""
from betelgeuse import collector
import mock


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


def test_source_markers():
    """Verifies if the test collection collects test markers."""
    config = mock.Mock()
    config.MARKERS_IGNORE_LIST = [
        'parametrize', 'skipif', 'usefixtures', 'skip_if_not_set']
    tests = collector.collect_tests('tests/data/test_sample.py', config=config)
    marked_test = [
        test for test in tests['tests/data/test_sample.py']
        if test.name == 'test_markers_sample'
    ].pop()
    assert marked_test.fields['markers'] == ('run_in_one_thread, tier1, '
                                             'on_prem_provisioning, osp')


def test_source_singular_module_marker():
    """Verifies the single module level marker is retrieved."""
    mod_string = 'import pytest\n\npytestmark = pytest.mark.tier2' \
                 '\n\ndef test_sing():\n\tpass'
    with open('/tmp/test_singular.py', 'w') as tfile:
        tfile.writelines(mod_string)

    config = mock.Mock()
    config.MARKERS_IGNORE_LIST = ['tier3']
    tests = collector.collect_tests('/tmp/test_singular.py', config=config)
    marked_test = [
        test for test in tests['/tmp/test_singular.py']
        if test.name == 'test_sing'
    ].pop()
    assert marked_test.fields['markers'] == 'tier2'
