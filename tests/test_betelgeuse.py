"""Betelgeuse unit tests."""
import click
import mock
import os
import pytest
import re

from click.testing import CliRunner
from betelgeuse import (
    INVALID_CHARS_REGEX,
    PylarionLibException,
    add_test_case,
    add_test_record,
    cli,
    create_xml_property,
    generate_test_steps,
    load_custom_fields,
    map_steps,
    parse_junit,
    parse_requirement_name,
    parse_test_results,
    validate_key_value_option,
)
from StringIO import StringIO
from xml.etree import ElementTree


JUNIT_XML = """<testsuite tests="4" skips="0">
    <testcase classname="foo1" name="test_passed" file="source.py" line="8">
    </testcase>
    <testcase classname="foo2" name="test_skipped">
        <skipped message="Skipped message">...</skipped>
    </testcase>
    <testcase classname="foo3" name="test_failure">
        <failure type="Type" message="Failure message">...</failure>
    </testcase>
    <testcase classname="foo4" name="test_error">
        <error type="ExceptionName" message="Error message">...</error>
    </testcase>
</testsuite>
"""

TEST_MODULE = '''  # noqa: Q000
def test_something():
    """This test something."""

def test_something_else():
    """This test something else."""
'''


MULTIPLE_STEPS = """<ol>
  <li><p>First step</p></li>
  <li><p>Second step</p></li>
  <li><p>Third step</p></li>
</ol>
"""

MULTIPLE_EXPECTEDRESULTS = """<ol>
  <li><p>First step expected result.</p></li>
  <li><p>Second step expected result.</p></li>
  <li><p>Third step expected result.</p></li>
</ol>
"""

SINGLE_STEP = """<p>Single step</p>"""

SINGLE_EXPECTEDRESULT = """<p>Single step expected result.</p>"""


@pytest.fixture
def cli_runner():
    """Return a `click`->`CliRunner` object."""
    return CliRunner()


def test_add_test_case_create():
    """Check if test case creation works."""
    obj_cache = {
        'collect_only': False,
        'project': 'PROJECT',
        'automation_script_format': '{path}@{line_number}'
    }
    with mock.patch.dict('betelgeuse.OBJ_CACHE', obj_cache):
        with mock.patch.multiple(
                'betelgeuse',
                Requirement=mock.DEFAULT,
                TestCase=mock.DEFAULT,
        ) as patches:
            patches['Requirement'].return_value = []
            test = mock.MagicMock()
            test.docstring = 'Test the name feature'
            test.function_def.lineno = 10
            test.module_def.path = 'path/to/test_module.py'
            test.name = 'test_name'
            test.parent_class = 'NameTestCase'
            test.testmodule = 'path/to/test_module.py'
            test.fields = {}
            test.fields['description'] = '<p>This is sample description</p>\n'
            # Add mixed case field key
            test.fields['CaseImportance'] = 'critical'
            add_test_case('path/to/test_module.py', test)
            patches['Requirement'].query.assert_called_once_with(
                'Module', fields=['title', 'work_item_id'])
            patches['Requirement'].create.assert_called_once_with(
                'PROJECT', 'Module', '', reqtype='functional')
            patches['TestCase'].query.assert_called_once_with(
                'path.to.test_module.NameTestCase.test_name',
                fields=[
                    'approvals',
                    'caseautomation',
                    'caseposneg',
                    'description',
                    'work_item_id',
                ]
            )
            patches['TestCase'].create.assert_called_once_with(
                'PROJECT',
                'test_name',
                '<p>This is sample description</p>\n',
                automation_script='path/to/test_module.py@10',
                caseautomation='automated',
                casecomponent='-',
                caseimportance='critical',
                caselevel='component',
                caseposneg='positive',
                setup=None,
                subtype1='-',
                test_case_id='path.to.test_module.NameTestCase.test_name',
                testtype='functional',
                upstream='no',
            )


def test_add_test_record():
    """Check if test record creation works."""
    test_run = mock.MagicMock()
    obj_cache = {
        'test_run': test_run,
        'user': 'testuser',
        'testcases': {
            'module.NameTestCase.test_name':
            'caffa7b0-fb9e-430b-903f-3f37fa28e0da',
        },
    }
    with mock.patch.dict('betelgeuse.OBJ_CACHE', obj_cache):
        with mock.patch.multiple(
                'betelgeuse',
                TestCase=mock.DEFAULT,
                collector=mock.DEFAULT,
                datetime=mock.DEFAULT,
        ) as patches:
            test_case = mock.MagicMock()
            patches['TestCase'].query.return_value = [test_case]
            test_function = mock.MagicMock()
            test_function.testmodule = 'module.py'
            test_function.parent_class = 'NameTestCase'
            test_function.name = 'test_name'
            patches['collector'].get_tests.return_value = {
                'module.py': [test_function],
            }
            add_test_record({
                'classname': 'module.NameTestCase',
                'message': u'Test failed because it not worked',
                'name': 'test_name',
                'status': 'failure',
                'time': '3.1415',
            })
            test_run.add_test_record_by_fields.assert_called_once_with(
                duration=3.1415,
                executed=patches['datetime'].datetime.now(),
                executed_by='testuser',
                test_case_id=test_case.work_item_id,
                test_comment='Test failed because it not worked',
                test_result='failed'
            )


def test_add_test_record_unexpected_exception():
    """Check if test record creation reraise unexpected exceptions."""
    class UnexpectedException(Exception):
        """Some unexpected exception."""

        pass
    test_run = mock.MagicMock()
    test_run.add_test_record_by_fields.side_effect = UnexpectedException(
        'UnexpectedException')
    obj_cache = {
        'test_run': test_run,
        'user': 'testuser',
        'testcases': {
            'module.NameTestCase.test_name':
            'caffa7b0-fb9e-430b-903f-3f37fa28e0da',
        },
    }
    with mock.patch.dict('betelgeuse.OBJ_CACHE', obj_cache):
        with mock.patch.multiple(
                'betelgeuse',
                TestCase=mock.DEFAULT,
                collector=mock.DEFAULT,
                datetime=mock.DEFAULT,
        ) as patches:
            test_case = mock.MagicMock()
            patches['TestCase'].query.return_value = [test_case]
            test_function = mock.MagicMock()
            test_function.testmodule = 'module.py'
            test_function.parent_class = 'NameTestCase'
            test_function.name = 'test_name'
            patches['collector'].get_tests.return_value = {
                'module.py': [test_function],
            }
            with pytest.raises(UnexpectedException) as excinfo:
                add_test_record({
                    'classname': 'module.NameTestCase',
                    'message': u'Test failed because it not worked',
                    'name': 'test_name',
                    'status': 'failure',
                    'time': '3.1415',
                })
            assert excinfo.value.message == 'UnexpectedException'


def test_generate_test_steps():
    """Check if test step generation works."""
    steps = [('Step1', 'Result1'), ('Step2', 'Result2')]
    with mock.patch.multiple(
            'betelgeuse',
            TestSteps=mock.DEFAULT,
            TestStep=mock.DEFAULT,
    ) as patches:
        patches['TestStep'].side_effect = [mock.MagicMock(), mock.MagicMock()]
        test_steps = generate_test_steps(steps)
    assert test_steps.keys == ['step', 'expectedResult']
    for step, expected in zip(test_steps.steps, steps):
        assert step.values == list(expected)


def test_load_custom_fields():
    """Check if custom fields can be loaded using = notation."""
    assert load_custom_fields(('isautomated=true',)) == {
        'isautomated': 'true'
    }


def test_load_custom_fields_empty():
    """Check if empty value return empty dict for custom fields."""
    assert load_custom_fields(('',)) == {}


def test_load_custom_fields_none():
    """Check if None value return empty dict for custom fields."""
    assert load_custom_fields(None) == {}


def test_load_custom_fields_json():
    """Check if custom fields can be loaded using JSON data."""
    assert load_custom_fields(('{"isautomated":true}',)) == {
        'isautomated': True,
    }


def test_map_single_step():
    """Check if mapping single step works."""
    mapped = [(SINGLE_STEP, SINGLE_EXPECTEDRESULT)]
    assert map_steps(SINGLE_STEP, SINGLE_EXPECTEDRESULT) == mapped


def test_map_multiple_steps():
    """Check if mapping multiple steps works."""
    assert map_steps(MULTIPLE_STEPS, MULTIPLE_EXPECTEDRESULTS) == [
        ('<p>First step</p>', '<p>First step expected result.</p>'),
        ('<p>Second step</p>', '<p>Second step expected result.</p>'),
        ('<p>Third step</p>', '<p>Third step expected result.</p>'),
    ]


def test_get_multiple_steps_diff_items():
    """Check if parsing multiple steps of different items works."""
    multiple_steps = '\n'.join(MULTIPLE_STEPS.splitlines()[:-2] + ['</ol>\n'])
    assert map_steps(
        multiple_steps, MULTIPLE_EXPECTEDRESULTS) == [(
            '<ol>\n  <li><p>First step</p></li>\n  '
            '<li><p>Second step</p></li>\n</ol>\n',
            MULTIPLE_EXPECTEDRESULTS
        )]


def test_parse_junit():
    """Check if jUnit parsing works."""
    junit_xml = StringIO(JUNIT_XML)
    assert parse_junit(junit_xml) == [
        {'classname': 'foo1', 'name': 'test_passed', 'status': 'passed',
         'line': '8', 'file': 'source.py'},
        {'classname': 'foo2', 'message': 'Skipped message',
         'name': 'test_skipped', 'status': 'skipped'},
        {'classname': 'foo3', 'name': 'test_failure',
         'message': 'Failure message', 'status': 'failure', 'type': 'Type'},
        {'classname': 'foo4', 'name': 'test_error', 'message': 'Error message',
         'status': 'error', 'type': 'ExceptionName'}
    ]
    junit_xml.close()


def test_invalid_test_run_chars_regex():
    """Check if invalid test run characters are handled."""
    invalid_test_run_id = '\\/.:*"<>|~!@#$?%^&\'*()+`,='
    assert re.sub(INVALID_CHARS_REGEX, '', invalid_test_run_id) == ''


def test_parse_requirement_name():
    """Check if parsing requirement name works."""
    assert parse_requirement_name(
        'tests/path/to/test_my_test_module.py') == 'My Test Module'


def test_parse_test_results():
    """Check if parsing test results works."""
    test_results = [
        {'status': u'passed',
         'name': 'test_positive_read',
         'classname': 'tests.api.test_ReadTestCase',
         'file': 'tests/api/test_foo.py',
         'time': '4.13224601746',
         'line': '521'},
        {'status': u'passed',
         'name': 'test_positive_delete',
         'classname': 'tests.api.test_ReadTestCase',
         'file': 'tests/api/test_foo.py',
         'time': '4.13224601746',
         'line': '538'},
        {'status': u'failure',
         'name': 'test_negative_read',
         'classname': 'tests.api.test_ReadTestCase',
         'file': 'tests/api/test_foo.py',
         'time': '4.13224601746',
         'line': '218'},
        {'status': u'skipped',
         'name': 'test_positive_update',
         'classname': 'tests.api.test_ReadTestCase',
         'file': 'tests/api/test_foo.py',
         'time': '4.13224601746',
         'line': '112'},
        {'status': u'error',
         'name': 'test_positive_create',
         'classname': 'tests.api.test_ReadTestCase',
         'file': 'tests/api/test_foo.py',
         'time': '4.13224601746',
         'line': '788'},
    ]
    summary = parse_test_results(test_results)
    assert summary['passed'] == 2
    assert summary['failure'] == 1
    assert summary['skipped'] == 1
    assert summary['error'] == 1


def test_test_case(cli_runner):
    """Check if test case command works."""
    with cli_runner.isolated_filesystem():
        with open('test_something.py', 'w') as handler:
            handler.write(TEST_MODULE)
        with mock.patch.multiple(
                'betelgeuse',
                TestCase=mock.DEFAULT,
                add_test_case=mock.DEFAULT,
                collector=mock.DEFAULT,
        ) as patches:
            result = cli_runner.invoke(
                cli,
                ['test-case', '--path', 'test_something.py', 'PROJECT']
            )
            assert result.exit_code == 0
            test_function = mock.MagicMock()
            tests = {
                'test_something.py': [test_function]
            }
            patches['collector'].collect_tests.items.return_value = tests
            patches['collector'].collect_tests('test_something.py')
            patches['add_test_case'].called_once_with(tests)


def test_test_case_skip_on_failure(cli_runner):
    """Check if test case create/update skips on failures."""
    with cli_runner.isolated_filesystem():
        with open('test_something.py', 'w') as handler:
            handler.write(TEST_MODULE)
        with mock.patch.multiple(
                'betelgeuse',
                add_test_case=mock.DEFAULT,
                collector=mock.DEFAULT,
        ) as patches:
            test_function = mock.MagicMock()
            tests = {
                'test_something.py': [test_function]
            }
            patches['collector'].collect_tests.return_value = tests
            patches['add_test_case'].side_effect = PylarionLibException
            result = cli_runner.invoke(
                cli,
                ['test-case', '--path', 'test_something.py', 'PROJECT']
            )
            assert result.exit_code == 0
            test_function.fields.get.assert_called_once_with(
                'title', test_function.name)


def test_test_plan(cli_runner):
    """Check if test-plan command runs with minimal parameters."""
    with mock.patch('betelgeuse.Plan') as plan:
        plan.search.return_value = []
        result = cli_runner.invoke(
            cli,
            [
                'test-plan',
                '--name', 'Test Plan Name',
                'PROJECT'
            ]
        )
        assert result.exit_code == 0
        plan.create.assert_called_once_with(
            parent_id=None,
            plan_id='Test_Plan_Name',
            plan_name='Test Plan Name',
            project_id='PROJECT',
            template_id='release',
        )


def test_test_plan_with_custom_fields(cli_runner):
    """Check if test-plan command runs with custom_fields."""
    with mock.patch('betelgeuse.Plan') as plan:
        test_plan = plan()
        test_plan.status = 'open'
        # Search will not return anything so new test plan will be created
        plan.search.return_value = []
        # Create command returns generated `test_plan` mock object
        plan.create.return_value = test_plan
        plan.update.return_value = []
        result = cli_runner.invoke(
            cli,
            [
                'test-plan',
                '--name',
                'Test Plan Name',
                '--custom-fields',
                'status=done',
                'PROJECT'
            ]
        )
        assert result.exit_code == 0
        plan.create.assert_called_once_with(
            parent_id=None,
            plan_id='Test_Plan_Name',
            plan_name='Test Plan Name',
            project_id='PROJECT',
            template_id='release',
        )
        assert test_plan.status == 'done'


def test_test_plan_with_parent(cli_runner):
    """Check if test-plan command runs when passing a parent test plan."""
    with mock.patch('betelgeuse.Plan') as plan:
        plan.search.return_value = []
        result = cli_runner.invoke(
            cli,
            [
                'test-plan',
                '--name', 'Test Plan Name',
                '--parent-name', 'Parent Test Plan Name',
                'PROJECT'
            ]
        )
        assert result.exit_code == 0
        plan.create.assert_called_once_with(
            parent_id='Parent_Test_Plan_Name',
            plan_id='Test_Plan_Name',
            plan_name='Test Plan Name',
            project_id='PROJECT',
            template_id='release',
        )


def test_test_plan_with_iteration_type(cli_runner):
    """Check if test-plan command creates a iteration test plan."""
    with mock.patch('betelgeuse.Plan') as plan:
        plan.search.return_value = []
        result = cli_runner.invoke(
            cli,
            [
                'test-plan',
                '--name', 'Test Plan Name',
                '--plan-type', 'iteration',
                'PROJECT'
            ]
        )
        assert result.exit_code == 0
        plan.create.assert_called_once_with(
            parent_id=None,
            plan_id='Test_Plan_Name',
            plan_name='Test Plan Name',
            project_id='PROJECT',
            template_id='iteration',
        )


def test_test_results(cli_runner):
    """Check if test results command works."""
    with cli_runner.isolated_filesystem():
        with open('results.xml', 'w') as handler:
            handler.write(JUNIT_XML)
        result = cli_runner.invoke(
            cli, ['test-results', '--path', 'results.xml'])
        assert result.exit_code == 0
        assert 'Error: 1\n' in result.output
        assert 'Failure: 1\n' in result.output
        assert 'Passed: 1\n' in result.output
        assert 'Skipped: 1\n' in result.output


def test_test_results_default_path(cli_runner):
    """Check if test results in the default path works."""
    with cli_runner.isolated_filesystem():
        with open('junit-results.xml', 'w') as handler:
            handler.write(JUNIT_XML)
        result = cli_runner.invoke(cli, ['test-results'])
        assert result.exit_code == 0
        assert 'Error: 1\n' in result.output
        assert 'Failure: 1\n' in result.output
        assert 'Passed: 1\n' in result.output
        assert 'Skipped: 1\n' in result.output


def test_test_run(cli_runner):
    """Check if test run command works."""
    with cli_runner.isolated_filesystem():
        with open('junit_report.xml', 'w') as handler:
            handler.write(JUNIT_XML)
        with mock.patch.multiple(
                'betelgeuse',
                TestRun=mock.DEFAULT,
                add_test_record=mock.DEFAULT,
                collector=mock.DEFAULT,
        ) as patches:
            result = cli_runner.invoke(
                cli,
                ['test-run', '--path', 'junit_report.xml', 'PROJECT']
            )
            assert result.exit_code == 0
            patches['TestRun'].session.tx_begin.assert_called_once_with()
            patches['TestRun'].session.tx_commit.assert_called_once_with()
            calls = [mock.call(r) for r in parse_junit('junit_report.xml')]
            patches['add_test_record'].assert_has_calls(calls)


def test_test_run_new_test_run(cli_runner):
    """Check if test run command works for a new test run."""
    with cli_runner.isolated_filesystem():
        with open('junit_report.xml', 'w') as handler:
            handler.write(JUNIT_XML)
        with mock.patch.multiple(
                'betelgeuse',
                TestRun=mock.DEFAULT,
                add_test_record=mock.DEFAULT,
                collector=mock.DEFAULT,
        ) as patches:
            patches['TestRun'].side_effect = PylarionLibException

            result = cli_runner.invoke(
                cli,
                [
                    'test-run',
                    '--path',
                    'junit_report.xml',
                    '--test-run-id',
                    'testrunid',
                    '--custom-fields',
                    '{"arch": "x86_64", "isautomated": true}',
                    'PROJECT'
                ]
            )
            assert result.exit_code == 0
            patches['TestRun'].create.assert_called_once_with(
                'PROJECT',
                'testrunid',
                'Empty',
                arch='x86_64',
                isautomated=True,
                type='buildacceptance',
            )
            patches['TestRun'].session.tx_begin.assert_called_once_with()
            patches['TestRun'].session.tx_commit.assert_called_once_with()
            calls = [mock.call(r) for r in parse_junit('junit_report.xml')]
            patches['add_test_record'].assert_has_calls(calls)


def test_create_xml_property():
    """Check if create_xml_property creates the expected XML tag."""
    generated = ElementTree.tostring(create_xml_property('name', 'value'))
    assert generated == '<property name="name" value="value" />'


def test_xml_test_run(cli_runner):
    """Check if xml test run command works."""
    with cli_runner.isolated_filesystem():
        with open('junit_report.xml', 'w') as handler:
            handler.write(JUNIT_XML)
        with open('source.py', 'w') as handler:
            handler.write('')
        with mock.patch('betelgeuse.collector') as collector:
            testcases = [
                {'name': 'test_passed', 'testmodule': 'foo1'},
                {'name': 'test_skipped', 'testmodule': 'foo2'},
                {'name': 'test_failure', 'testmodule': 'foo3'},
                {'name': 'test_error', 'testmodule': 'foo4'},
            ]
            return_value_testcases = []
            for test in testcases:
                t = mock.MagicMock()
                t.name = test['name']
                t.testmodule = test['testmodule']
                t.parent_class = None
                t.fields = {'id': str(id(t))}
                return_value_testcases.append(t)

            collector.collect_tests.return_value = {
                'source.py': return_value_testcases,
            }
            result = cli_runner.invoke(
                cli,
                [
                    'xml-test-run',
                    '--dry-run',
                    '--no-include-skipped',
                    '--custom-fields', 'field=value',
                    '--response-property', 'key=value',
                    '--status', 'inprogress',
                    '--test-run-id', 'test-run-id',
                    '--test-run-template-id', 'test-run-template-id',
                    '--test-run-title', 'test-run-title',
                    '--test-run-type-id', 'test-run-type-id',
                    'junit_report.xml',
                    'source.py',
                    'userid',
                    'projectid',
                    'importer.xml'
                ]
            )
            assert result.exit_code == 0
            collector.collect_tests.assert_called_once_with('source.py')
            assert os.path.isfile('importer.xml')
            root = ElementTree.parse('importer.xml').getroot()
            assert root.tag == 'testsuites'
            properties = root.find('properties')
            assert properties
            properties = [p.attrib for p in properties.findall('property')]
            expected = [
                {'name': 'polarion-custom-field', 'value': 'value'},
                {'name': 'polarion-dry-run', 'value': 'true'},
                {'name': 'polarion-include-skipped', 'value': 'false'},
                {'name': 'polarion-lookup-method', 'value': 'custom'},
                {'name': 'polarion-project-id', 'value': 'projectid'},
                {'name': 'polarion-response-key', 'value': 'value'},
                {'name': 'polarion-set-testrun-finished', 'value': 'false'},
                {'name': 'polarion-testrun-id', 'value': 'test-run-id'},
                {'name': 'polarion-testrun-template-id',
                 'value': 'test-run-template-id'},
                {'name': 'polarion-testrun-title', 'value': 'test-run-title'},
                {'name': 'polarion-testrun-type-id',
                 'value': 'test-run-type-id'},
                {'name': 'polarion-user-id', 'value': 'userid'},
            ]
            for p in properties:
                assert p in expected
            testsuite = root.find('testsuite')
            assert testsuite
            for index, testcase in enumerate(testsuite.findall('testcase')):
                properties = testcase.find('properties')
                assert properties
                p = properties.findall('property')
                assert len(p) == 1
                p = p[0]
                assert p.attrib == {
                    'name': 'polarion-testcase-id',
                    'value': str(id(return_value_testcases[index]))
                }


def test_validate_key_value_option():
    """Check if validate_key_value_option works."""
    # None value will be passed when the option is not specified.
    for value, result in (('key=value=', ('key', 'value=')), (None, None)):
        assert validate_key_value_option(
            None, mock.MagicMock(), value) == result


def test_validate_key_value_option_exception():
    """Check if validate_key_value_option validates invalid values."""
    option = mock.MagicMock()
    option.name = 'option_name'
    msg = 'option_name needs to be in format key=value'
    for value in ('value', ''):
        with pytest.raises(click.BadParameter) as excinfo:
            validate_key_value_option(None, option, value)
        assert excinfo.value.message == msg
