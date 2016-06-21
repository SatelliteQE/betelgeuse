import betelgeuse
import click
import mock
import pytest
import re

from click.testing import CliRunner
from betelgeuse import (
    INVALID_TEST_RUN_CHARS_REGEX,
    RST_PARSER,
    JobNumberParamType,
    PylarionLibException,
    add_test_case,
    add_test_record,
    cli,
    parse_junit,
    parse_requirement_name,
    parse_test_results,
)
from StringIO import StringIO


JUNIT_XML = """<testsuite tests="4">
    <testcase classname="foo1" name="test_passed"></testcase>
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

TEST_MODULE = '''
def test_something():
    """This test something."""

def test_something_else():
    """This test something else."""
'''


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_add_test_case_create():
    obj_cache = {
        'collect_only': False,
        'project': 'PROJECT',
    }
    with mock.patch.dict('betelgeuse.OBJ_CACHE', obj_cache):
        with mock.patch.multiple(
                'betelgeuse',
                Requirement=mock.DEFAULT,
                TestCase=mock.DEFAULT,
        ) as patches:
            patches['Requirement'].return_value = []
            test = mock.MagicMock()
            test.name = 'test_name'
            test.docstring = 'Test the name feature'
            test.parent_class = 'NameTestCase'
            test.tokens = {}
            add_test_case(('path/to/test_module.py', [test]))
            patches['Requirement'].query.assert_called_once_with(
                'Module', fields=['title', 'work_item_id'])
            patches['Requirement'].create.assert_called_once_with(
                'PROJECT', 'Module', '', reqtype='functional')
            patches['TestCase'].query.assert_called_once_with(
                'path.to.test_module.NameTestCase.test_name',
                fields=[
                    'caseautomation',
                    'caseposneg',
                    'description',
                    'work_item_id',
                ]
            )
            patches['TestCase'].create.assert_called_once_with(
                'PROJECT',
                'test_name',
                '<p>Test the name feature</p>\n',
                caseautomation='automated',
                casecomponent='-',
                caseimportance='medium',
                caselevel='component',
                caseposneg='positive',
                setup=None,
                subtype1='-',
                test_case_id='path.to.test_module.NameTestCase.test_name',
                testtype='functional',
                upstream='no',
            )


def test_add_test_record():
    test_run = mock.MagicMock()
    obj_cache = {
        'test_run': test_run,
        'user': 'testuser',
    }
    with mock.patch.dict('betelgeuse.OBJ_CACHE', obj_cache):
        with mock.patch.multiple(
                'betelgeuse',
                TestCase=mock.DEFAULT,
                datetime=mock.DEFAULT,
        ) as patches:
            test_case = mock.MagicMock()
            patches['TestCase'].query.return_value = [test_case]
            add_test_record({
                'classname': 'NameTestCase',
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


def test_parse_junit():
    junit_xml = StringIO(JUNIT_XML)
    assert parse_junit(junit_xml) == [
        {'classname': 'foo1', 'name': 'test_passed', 'status': 'passed'},
        {'classname': 'foo2', 'message': 'Skipped message',
         'name': 'test_skipped', 'status': 'skipped'},
        {'classname': 'foo3', 'name': 'test_failure',
         'message': 'Failure message', 'status': 'failure', 'type': 'Type'},
        {'classname': 'foo4', 'name': 'test_error', 'message': 'Error message',
         'status': 'error', 'type': 'ExceptionName'}
    ]
    junit_xml.close()


def test_rst_parser():
    docstring = """Line one"""
    generated_html = "<p>Line one</p>\n"
    assert RST_PARSER.parse(docstring) == generated_html


def test_invalid_test_run_chars_regex():
    invalid_test_run_id = '\\/.:*"<>|~!@#$?%^&\'*()+`,='
    assert re.sub(INVALID_TEST_RUN_CHARS_REGEX, '', invalid_test_run_id) == ''


def test_job_param_type():
    job_param = JobNumberParamType()
    with mock.patch('betelgeuse.multiprocessing') as multiprocessing:
        job_param.convert('auto', None, None)
        multiprocessing.cpu_count.assert_called_once_with()
    with pytest.raises(click.BadParameter):
        job_param.convert('-1', None, None)


def test_parse_requirement_name():
    assert parse_requirement_name(
        'tests/path/to/test_my_test_module.py') == 'My Test Module'


def test_parse_test_results():
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
    with cli_runner.isolated_filesystem():
        with open('test_something.py', 'w') as handler:
            handler.write(TEST_MODULE)
        with mock.patch.multiple(
                'betelgeuse',
                TestCase=mock.DEFAULT,
                multiprocessing=mock.DEFAULT,
                testimony=mock.DEFAULT
        ) as patches:
            pool = mock.MagicMock()
            patches['multiprocessing'].Pool.return_value = pool

            result = cli_runner.invoke(
                cli,
                ['test-case', '--path', 'test_something.py', 'PROJECT']
            )
            assert result.exit_code == 0
            pool.map.assert_called_once_with(
                betelgeuse.add_test_case,
                patches['testimony'].get_testcases().items()
            )
            pool.close.assert_called_once_with()
            pool.join.assert_called_once_with()


def test_test_results(cli_runner):
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
    with cli_runner.isolated_filesystem():
        with open('junit_report.xml', 'w') as handler:
            handler.write(JUNIT_XML)
        with mock.patch.multiple(
                'betelgeuse',
                TestRun=mock.DEFAULT,
                multiprocessing=mock.DEFAULT,
                testimony=mock.DEFAULT
        ) as patches:
            pool = mock.MagicMock()
            patches['multiprocessing'].Pool.return_value = pool

            result = cli_runner.invoke(
                cli,
                ['test-run', '--path', 'junit_report.xml', 'PROJECT']
            )
            assert result.exit_code == 0
            patches['TestRun'].session.tx_begin.assert_called_once_with()
            patches['TestRun'].session.tx_commit.assert_called_once_with()
            pool.map.assert_called_once_with(
                betelgeuse.add_test_record,
                parse_junit('junit_report.xml')
            )
            pool.close.assert_called_once_with()
            pool.join.assert_called_once_with()


def test_test_run_new_test_run(cli_runner):
    with cli_runner.isolated_filesystem():
        with open('junit_report.xml', 'w') as handler:
            handler.write(JUNIT_XML)
        with mock.patch.multiple(
                'betelgeuse',
                TestRun=mock.DEFAULT,
                multiprocessing=mock.DEFAULT,
                testimony=mock.DEFAULT
        ) as patches:
            pool = mock.MagicMock()
            patches['multiprocessing'].Pool.return_value = pool
            patches['TestRun'].side_effect = PylarionLibException

            result = cli_runner.invoke(
                cli,
                [
                    'test-run',
                    '--path', 'junit_report.xml',
                    '--test-run-id', 'testrunid',
                    'PROJECT'
                ]
            )
            assert result.exit_code == 0
            patches['TestRun'].create.assert_called_once_with(
                'PROJECT', 'testrunid', 'Empty')
            patches['TestRun'].session.tx_begin.assert_called_once_with()
            patches['TestRun'].session.tx_commit.assert_called_once_with()
            pool.map.assert_called_once_with(
                betelgeuse.add_test_record,
                parse_junit('junit_report.xml')
            )
            pool.close.assert_called_once_with()
            pool.join.assert_called_once_with()
