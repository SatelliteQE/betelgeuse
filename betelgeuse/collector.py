# coding=utf-8
"""Tools to walk a path and collect test methods and functions."""
import ast
import collections
import fnmatch
import os

from betelgeuse.parser import parse_docstring


class TestFunction(object):
    """Wrapper for ``ast.FunctionDef`` which parse docstring information."""

    def __init__(self, function_def, parent_class=None, testmodule=None):
        """``ast.FunctionDef`` instance used to extract information."""
        self.docstring = ast.get_docstring(function_def)
        self.function_def = function_def
        self.name = function_def.name
        if parent_class:
            self.parent_class = parent_class.name
            self.parent_class_def = parent_class
            self.class_docstring = ast.get_docstring(self.parent_class_def)
        else:
            self.parent_class = None
            self.parent_class_def = None
            self.class_docstring = None
        self.testmodule = testmodule.path
        self.module_def = testmodule
        self.module_docstring = ast.get_docstring(self.module_def)
        self.pkginit = os.path.join(
            os.path.dirname(self.testmodule), '__init__.py')
        if os.path.exists(self.pkginit):
            self.pkginit_def = ast.parse(''.join(open(self.pkginit)))
            self.pkginit_docstring = ast.get_docstring(self.pkginit_def)
        else:
            self.pkginit_def = None
            self.pkginit_docstring = None
        self.fields = {}
        self._parse_docstring()

    def _parse_docstring(self):
        """Parse package, module, class and function docstrings."""
        if self.docstring is None:
            return

        # Parse package, module, class and function docstrings. Every loop
        # updates the already defined fields. The order of processing ensures
        # that function docstring has more priority over class and module and
        # package docstrings respectively.
        docstrings = [
            self.pkginit_docstring,
            self.module_docstring,
            self.class_docstring,
            self.docstring,
        ]
        for docstring in docstrings:
            if docstring and not isinstance(docstring, type(u'')):
                docstring = docstring.decode('utf-8')
            self.fields.update(parse_docstring(docstring))


def is_test_module(filename):
    """Indicate if ``filename`` match a test module file name."""
    for pat in ('test_*.py', '*_test.py'):
        if fnmatch.fnmatch(filename, pat):
            return True
    return False


def _get_tests(path):
    """Collect tests for the test module located at ``path``."""
    tests = []
    with open(path) as handler:
        root = ast.parse(handler.read())
        root.path = path  # TODO improve how to pass the path to TestFunction
        for node in ast.iter_child_nodes(root):
            if isinstance(node, ast.ClassDef):
                [
                    tests.append(TestFunction(subnode, node, root))
                    for subnode in ast.iter_child_nodes(node)
                    if isinstance(subnode, ast.FunctionDef) and
                    subnode.name.startswith('test_')
                ]
            elif (isinstance(node, ast.FunctionDef) and
                    node.name.startswith('test_')):
                tests.append(TestFunction(node, testmodule=root))
    return tests


def collect_tests(path):
    """Walk ``path`` and collect test methods and functions found.

    :param path: Either a file or directory path to look for test methods and
        functions.
    :return: A dict mapping a test module path and its test cases.
    """
    tests = collections.OrderedDict()
    if os.path.isfile(path):
        if is_test_module(os.path.basename(path)):
            tests[path] = _get_tests(path)
            return tests
    for dirpath, _, filenames in os.walk(path):
        for filename in filenames:
            if is_test_module(filename):
                path = os.path.join(dirpath, filename)
                tests[path] = _get_tests(path)
    return tests
