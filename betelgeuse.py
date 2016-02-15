"""Betelgeuse.

Betelgeuse reads standard Python test cases and offers tools to interact with
Polarion. Possible interactions:

* Automatic creation of Requirements and Test Cases from a Python
  project code base and jUnit XML file.
* Synchronization of Test Cases from a Python project code base
  and jUnit XML file.
* Creation of Test Runs based on a jUnit XML file.
"""
import click
import datetime
import logging
import multiprocessing
import re
import ssl
import testimony
import time

from collections import Counter
from pylarion.exceptions import PylarionLibException
from pylarion.work_item import TestCase, Requirement
from pylarion.test_run import TestRun
from xml.etree import ElementTree

logging.captureWarnings(True)

# Avoid SSL errors
ssl._create_default_https_context = ssl._create_unverified_context

INVALID_TEST_RUN_CHARS_REGEX = re.compile(r'[\\/.:"<>|~!@#$?%^&\'*()+`,=]')

POLARION_STATUS = {
    'error': 'failed',
    'failure': 'failed',
    'passed': 'passed',
    'skipped': 'blocked',
}

JUNIT_TEST_STATUS = ['error', 'failure', 'skipped']

# Cache for shared objects
OBJ_CACHE = {}


class JobNumberParamType(click.ParamType):
    """Number of jobs click param type.

    This param type accepts ``auto`` or any positive integer (>0) as valid
    values.
    """
    name = 'job number'

    def convert(self, value, param, context):
        if value.lower() == 'auto':
            return multiprocessing.cpu_count()
        try:
            value = int(value)
            if value <= 0:
                raise ValueError('{0} is not a positive integer'.format(value))
            return value
        except ValueError:
            self.fail(
                '{0} is not a positive integer'.format(value), param, context)


JOB_NUMBER = JobNumberParamType()


def parse_requirement_name(path):
    """Return the Requirement name for a given path.

    The path ``tests/path/to/test_my_test_module.py`` will produce the
    requirement name ``My Test Module``.

    :param path: path to a test module.
    """
    return (
        path.split('/')[-1].replace('test_', '', 1).replace('.py', '')
        .replace('_', ' ').title()
    )


def parse_junit(path):
    """Parse a jUnit XML file.

    Given the following jUnit file::

        <testsuite tests="3">
            <testcase classname="foo1" name="test_passed"></testcase>
            <testcase classname="foo2" name="test_skipped">
                <skipped message="...">...</skipped>
            </testcase>
            <testcase classname="foo3" name="test_failure">
                <failure type="Type" message="...">...</failure>
            </testcase>
            <testcase classname="foo3" name="test_error">
                <error type="ExceptionName" message="...">...</error>
            </testcase>
        </testsuite>

    The return will be::

        [
            {'classname': 'foo1', 'name': 'test_passed', 'status': 'passed'},
            {'classname': 'foo2', 'message': '...', 'name': 'test_skipped',
             'status': 'skipped'},
            {'classname': 'foo3', 'name': 'test_failure', 'status': 'passed'},
            {'classname': 'foo3', 'name': 'test_error', 'status': 'passed'}
        ]

    :param str path: Path to the jUnit XML file.
    :return: A list of dicts with information about every test
        case result.
    """
    root = ElementTree.parse(path).getroot()
    result = []
    for testcase in root.iter('testcase'):
        data = testcase.attrib
        # Check if the test has passed or else...
        status = [
            element for element in list(testcase)
            if element.tag in JUNIT_TEST_STATUS
        ]
        # ... no status means the test has passed
        if status:
            data['status'] = status[0].tag
            data.update(status[0].attrib)
        else:
            data['status'] = u'passed'

        result.append(data)
    return result


def parse_test_results(test_results):
    """Returns the summary of test results by their status.

    :param test_results: A list of dicts with information about
        test results, such as those reported in a jUnit file.
    :return: A dictionary containing a summary for all test results
        provided by the ``test_results`` parameter, broken down by their
        status.
    """
    return Counter([test['status'] for test in test_results])


def add_test_case(args):
    """Task that creates or updates Test Cases and manages their Requirement.

    This task relies on ``OBJ_CACHE`` to get the collect_only and project
    objects.

    :param args: A tuple where the first element is a path and the second is a
        list of ``TestFunction`` objects mapping the tests from that path.
    """
    path, tests = args
    collect_only = OBJ_CACHE['collect_only']
    project = OBJ_CACHE['project']

    # Fetch or create a Requirement
    requirement = None
    requirement_name = parse_requirement_name(path)
    click.echo(
        'Fetching requirement {0}.'.format(requirement_name))
    if not collect_only:
        results = Requirement.query(
            '{0}'.format(requirement_name),
            fields=['title', 'work_item_id']
        )
        if len(results) > 0:
            # As currently is not possible to get a single
            # match for the title, make sure to not use a
            # not intended Requirement.
            for result in results:
                if result.title == requirement_name:
                    requirement = result
    if requirement is None:
        click.echo(
            'Creating requirement {0}.'.format(requirement_name))
        if not collect_only:
            requirement = Requirement.create(
                project,
                requirement_name,
                '',
                reqtype='functional'
            )

    for test in tests:
        # Generate the test_case_id. It could be either path.test_name or
        # path.ClassName.test_name if the test methods is defined within a
        # class.
        test_case_id_parts = [
            path.replace('/', '.').replace('.py', ''),
            test.name
        ]
        if test.parent_class is not None:
            test_case_id_parts.insert(-1, test.parent_class)
        test_case_id = '.'.join(test_case_id_parts)

        if test.docstring:
            if not type(test.docstring) == unicode:
                test.docstring = test.docstring.decode('utf8')
            test.docstring = u'<pre>{0}</pre>'.format(test.docstring)
            test.docstring = test.docstring.encode(
                'ascii', 'xmlcharrefreplace')

        # Is the test automated? Acceptable values are:
        # automated, manualonly, and notautomated
        auto_status = 'automated' if test.automated else 'notautomated'

        results = []
        if not collect_only:
            results = TestCase.query(
                test_case_id, fields=['description', 'work_item_id'])
        if len(results) == 0:
            click.echo(
                'Creating test case {0} for requirement {1}.'
                .format(test.name, requirement_name)
            )
            if not collect_only:
                test_case = TestCase.create(
                    project,
                    test.name,
                    test.docstring if test.docstring else '',
                    caseautomation=auto_status,
                    casecomponent='-',
                    caseimportance='medium',
                    caselevel='component',
                    caseposneg='positive',
                    subtype1='-',
                    test_case_id=test_case_id,
                    testtype='functional',
                )
            click.echo(
                'Linking test case {0} to verify requirement {1}.'
                .format(test.name, requirement_name)
            )
            if not collect_only:
                test_case.add_linked_item(
                    requirement.work_item_id, 'verifies')
        else:
            click.echo(
                'Updating test case {0} for requirement {1}.'
                .format(test.name, requirement_name)
            )
            # Ensure that a single match for the Test Case is
            # returned.
            assert len(results) == 1
            # Fetch the test case in order to get all of its
            # fields and values.
            test_case = TestCase(project, results[0].work_item_id)
            if (not collect_only and
                (test_case.description != test.docstring or
                    test_case.caseautomation != auto_status)):
                test_case.description = (
                    test.docstring if test.docstring else '')
                test_case.caseautomation = auto_status
                test_case.update()


def add_test_record(result):
    """Task that adds a test result to a test run.

    This task relies on ``OBJ_CACHE`` to get the test run and user objects. The
    object cache is needed since suds objects are not able to be pickled and it
    is not possible to pass them to processes.
    """
    test_run = OBJ_CACHE['test_run']
    user = OBJ_CACHE['user']
    test_case_id = '{0}.{1}'.format(result['classname'], result['name'])
    test_case = TestCase.query(test_case_id)
    if len(test_case) == 0:
        click.echo(
            'Was not able to find test case with id {0}, skipping...'
            .format(test_case_id)
        )
        return
    status = POLARION_STATUS[result['status']]
    work_item_id = test_case[0].work_item_id
    click.echo(
        'Adding test record for test case {0} with status {1}.'
        .format(work_item_id, status)
    )
    message = result.get('message')
    if message and type(message) == unicode:
        message = message.encode('ascii', 'xmlcharrefreplace')
    try:
        test_run.add_test_record_by_fields(
            test_case_id=work_item_id,
            test_result=status,
            test_comment=message,
            executed_by=user,
            executed=datetime.datetime.now(),
            duration=float(result.get('time', '0'))
        )
    except PylarionLibException as err:
        click.echo('Skipping test case {0}.'.format(work_item_id))
        click.echo(err, err=True)


@click.group()
@click.option(
    '--jobs',
    '-j',
    default='1',
    help='Number of jobs or auto to use the CPU count.',
    type=JOB_NUMBER
)
@click.pass_context
def cli(context, jobs):
    """Betelgeuse CLI command group."""
    context.obj = {}
    context.obj['jobs'] = jobs


@cli.command('test-case')
@click.option(
    '--path',
    default='tests',
    help='Path to the test module or directory.',
    type=click.Path(exists=True),
)
@click.option(
    '--collect-only',
    help=('Not perform any operation on Polarion, just prints '
          'collected information.'),
    is_flag=True,
)
@click.argument('project')
@click.pass_context
def test_case(context, path, collect_only, project):
    """Sync test cases with Polarion."""
    testcases = testimony.get_testcases([path])
    OBJ_CACHE['collect_only'] = collect_only
    OBJ_CACHE['project'] = project

    if not collect_only:
        TestCase.session.tx_begin()
    pool = multiprocessing.Pool(context.obj['jobs'])
    pool.map(add_test_case, testcases.items())
    pool.close()
    pool.join()
    if not collect_only:
        TestCase.session.tx_commit()


@cli.command('test-results')
@click.option(
    '--path',
    default='junit-results.xml',
    help='Path to the jUnit XML file.',
    type=click.Path(exists=True, dir_okay=False),
)
def test_results(path):
    """Shows a summary for test cases contained in a jUnit XML file."""
    test_summary = parse_test_results(parse_junit(path))
    summary = '\n'.join(
        ["{0}: {1}".format(*status) for status in test_summary.items()]
    ).title()
    click.echo(summary)


@cli.command('test-run')
@click.option(
    '--path',
    default='junit-results.xml',
    help='Path to the jUnit XML file.',
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    '--test-run-id',
    default='test-run-{0}'.format(time.time()),
    help='Test Run ID to be created/updated.',
)
@click.option(
    '--test-template-id',
    default='Empty',
    help='Test Template ID to create the Test Run.',
)
@click.option(
    '--user',
    default='betelgeuse',
    help='User that is executing the Test Run.',
)
@click.argument('project')
@click.pass_context
def test_run(context, path, test_run_id, test_template_id, user, project):
    """Execute a test run based on jUnit XML file."""
    test_run_id = re.sub(INVALID_TEST_RUN_CHARS_REGEX, '', test_run_id)
    results = parse_junit(path)
    try:
        test_run = TestRun(test_run_id, project_id=project)
        click.echo('Test run {0} found.'.format(test_run_id))
    except PylarionLibException as err:
        click.echo(err, err=True)
        click.echo('Creating test run {0}.'.format(test_run_id))
        test_run = TestRun.create(project, test_run_id, test_template_id)

    OBJ_CACHE['test_run'] = test_run
    OBJ_CACHE['user'] = user

    TestRun.session.tx_begin()
    pool = multiprocessing.Pool(context.obj['jobs'])
    pool.map(add_test_record, results)
    pool.close()
    pool.join()
    TestRun.session.tx_commit()
