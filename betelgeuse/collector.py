# coding=utf-8
"""Tools to walk a path and collect test methods and functions."""
import ast
import collections
import fnmatch
import os

from betelgeuse.parser import parse_docstring
from betelgeuse.source_generator import gen_source


class TestFunction(object):
    """Wrapper for ``ast.FunctionDef`` which parse docstring information."""

    def __init__(self, function_def, parent_class=None, testmodule=None):
        """``ast.FunctionDef`` instance used to extract information."""
        #: The unparsed testcase docstring
        self.docstring = ast.get_docstring(function_def)
        #: The ``ast.FunctionDef`` representation of the testcase method or
        #: function
        self.function_def = function_def
        #: The testcase function or method name
        self.name = function_def.name
        if parent_class:
            #: If the testcase is a method then the parent class name will be
            #: set, otherwise it will be ``None``
            self.parent_class = parent_class.name
            #: If the testcase is a method then the parent ``ast.ClasDef``
            #: representation of the parent calss will be set, otherwise it
            #: will be ``None``
            self.parent_class_def = parent_class
            #: If test case is a method then the parent class docstring will be
            #: set, otherwise it will be ``None``
            self.class_docstring = ast.get_docstring(self.parent_class_def)
        else:
            self.parent_class = None
            self.parent_class_def = None
            self.class_docstring = None
        #: The parent module path in Python import path notation
        self.testmodule = testmodule.path
        #: The parent module ``ast.Module`` representation.
        self.module_def = testmodule
        #: The parent module docstring
        self.module_docstring = ast.get_docstring(self.module_def)
        #: The ``__init__.py`` path for the package containing the test module
        #: if it existis, or ``None`` otherwise
        self.pkginit = os.path.join(
            os.path.dirname(self.testmodule), '__init__.py')
        if os.path.exists(self.pkginit):
            #: If ``__init__.py`` module exists, this will be the
            #: ``ast.Module`` representation of that module, it will be
            #: ``None`` otherwise
            self.pkginit_def = ast.parse(''.join(open(self.pkginit)))
            #: If ``__init__.py`` module exists, this will be the
            #: docstring of that module, it will be ``None`` otherwise
            self.pkginit_docstring = ast.get_docstring(self.pkginit_def)
        else:
            self.pkginit = None
            self.pkginit_def = None
            self.pkginit_docstring = None
        #: The dictionary that will store the field values defined for the
        #: testcase. The field value resolution order is the test funtion or
        #: method docstring, the class docstring if it is a method, the module
        #: docstring and finally the ``__init__.py`` docstring if present. The
        #: first value found the search will stop.
        self.fields = {}
        #: The list of decorators applied to this testcase
        self.decorators = [
            gen_source(decorator)
            for decorator in self.function_def.decorator_list
        ]
        #: The list of decorators applied to this testcase's parent class. If
        #: this testcase doesn'node have a parent class, then it will be
        #: ``None``
        self.class_decorators = None
        if self.parent_class_def:
            self.class_decorators = [
                gen_source(decorator)
                for decorator in self.parent_class_def.decorator_list
            ]
        self._parse_docstring()
        self.junit_id = self._generate_junit_id()

        if 'id' not in self.fields:
            self.fields['id'] = self.junit_id

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

    def _generate_junit_id(self):
        """Generate the jUnit ID for the test.

        It could be either ``path.to.module.test_name`` or
        ``path.to.module.ClassName.test_name`` if the test methods is defined
        within a class.
        """
        test_case_id_parts = [
            self.testmodule.replace('/', '.').replace('.py', ''),
            self.name
        ]
        if self.parent_class is not None:
            test_case_id_parts.insert(-1, self.parent_class)
        return '.'.join(test_case_id_parts)


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


def collect_tests(path, ignore_paths=None):
    """Walk ``path`` and collect test methods and functions found.

    :param path: Either a file or directory path to look for test methods and
        functions.
    :return: A dict mapping a test module path and its test cases.
    """
    path = os.path.normpath(path)
    if not ignore_paths:
        ignore_paths = ()
    tests = collections.OrderedDict()
    if os.path.isfile(path) and path not in ignore_paths:
        if is_test_module(os.path.basename(path)):
            tests[path] = _get_tests(path)
            return tests
    for dirpath, _, filenames in os.walk(path):
        if dirpath in ignore_paths:
            continue
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            if path in ignore_paths:
                continue
            if is_test_module(filename):
                tests[path] = _get_tests(path)
    return tests
