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
import ssl
import testimony
import time

from pylarion.exceptions import PylarionLibException
from pylarion.work_item import TestCase, Requirement
from pylarion.test_run import TestRun
from xml.etree import ElementTree

logging.captureWarnings(True)

# Avoid SSL errors
ssl._create_default_https_context = ssl._create_unverified_context

POLARION_STATUS = {
    'error': 'failed',
    'failure': 'failed',
    'passed': 'passed',
    'skipped': 'blocked',
}

JUNIT_TEST_STATUS = ['error', 'failure', 'skipped']


def parse_requirement_name(test_case_id):
    """Return the Requirement name for a given test_case_id."""
    index = -2
    parts = test_case_id.split('.')
    if parts[index][0].isupper():
        index -= 1
    return parts[index].replace('test_', '').replace('_', ' ').title()


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


@click.group()
def cli():
    """Betelgeuse CLI command group."""
    pass


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
def test_case(path, collect_only, project):
    """Sync test cases with Polarion."""
    testcases = testimony.get_testcases([path])
    for path, tests in testcases.items():
        requirement = None
        for test in tests:
            # Expect test_case_id to be path.test_name or
            # path.ClassName.test_name.
            test_case_id_parts = [
                path.replace('/', '.').replace('.py', ''),
                test.name
            ]
            if test.parent_class is not None:
                test_case_id_parts.insert(-1, test.parent_class)
            test_case_id = '.'.join(test_case_id_parts)
            if requirement is None:
                requirement_name = parse_requirement_name(test_case_id)
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

            if test.docstring:
                if not type(test.docstring) == unicode:
                    test.docstring = test.docstring.decode('utf8')
                test.docstring = u'<pre>{0}</pre>'.format(test.docstring)
                test.docstring = test.docstring.encode(
                    'ascii', 'xmlcharrefreplace')

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
                        caseautomation='automated',
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
                test_case = results[0]
                if (not collect_only and
                        test_case.description != test.docstring):
                    test_case = TestCase(project, test_case.work_item_id)
                    test_case.description = (
                        test.docstring if test.docstring else '')
                    test_case.update()


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
def test_run(path, test_run_id, test_template_id, user, project):
    """Execute a test run based on jUnit XML file."""
    results = parse_junit(path)
    try:
        test_run = TestRun(test_run_id, project_id=project)
        click.echo('Test run {0} found.'.format(test_run_id))
    except PylarionLibException as err:
        click.echo(err, err=True)
        click.echo('Creating test run {0}.'.format(test_run_id))
        test_run = TestRun.create(project, test_run_id, test_template_id)

    for result in results:
        test_case_id = '{0}.{1}'.format(result['classname'], result['name'])
        test_case = TestCase.query(test_case_id)
        if len(test_case) == 0:
            click.echo(
                'Was not able to find test case with id {0}, skipping...'
                .format(test_case_id)
            )
            continue
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
