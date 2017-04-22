# coding=utf-8
"""Tests for :mod:`betelgeuse.collector`."""
import pytest

from betelgeuse import collector


@pytest.mark.parametrize('path', ('tests/data', 'tests/data/test_sample.py'))
def test_collect_tests(path):
    """Check if ``collect_tests`` 'tests/data'collect tests."""
    tests = collector.collect_tests(path)
    assert 'tests/data/test_sample.py' in tests
    assert len(tests['tests/data/test_sample.py']) == 3


@pytest.mark.parametrize('filename', ('test_module.py', 'module_test.py'))
def test_is_test_module(filename):
    """Check ``is_test_module`` working for valid filenames."""
    assert collector.is_test_module(filename)


@pytest.mark.parametrize('filename', ('not_test_module.py', 'module.py'))
def test_not_is_test_module(filename):
    """Check ``is_test_module`` working for invalid filenames."""
    assert not collector.is_test_module(filename)
