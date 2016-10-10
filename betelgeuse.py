"""Betelgeuse.

Betelgeuse reads standard Python test cases and offers tools to interact with
Polarion. Possible interactions:

* Automatic creation of Requirements and Test Cases from a Python
  project code base and jUnit XML file.
* Synchronization of Test Cases from a Python project code base
  and jUnit XML file.
* Creation of Test Runs based on a jUnit XML file.
"""
import datetime
import docutils
import docutils.core
import docutils.io
import itertools
import json
import logging
import multiprocessing
import re
import ssl
import time
import traceback
from collections import Counter
from xml.dom import minidom
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError

import click
import testimony
from pylarion.exceptions import PylarionLibException
from pylarion.work_item import (
    Requirement,
    TestCase,
    TestStep,
    TestSteps,
)
from pylarion.plan import Plan
from pylarion.test_run import TestRun
from testimony.cli import _validate_token_prefix


logging.captureWarnings(True)

# Avoid SSL errors
ssl._create_default_https_context = ssl._create_unverified_context

INVALID_CHARS_REGEX = re.compile(r'[\\/.:"<>|~!@#$?%^&\'*()+`,=]')

POLARION_STATUS = {
    'error': 'failed',
    'failure': 'failed',
    'passed': 'passed',
    'skipped': 'blocked',
}

JUNIT_TEST_STATUS = ['error', 'failure', 'skipped']

# Cache for shared objects
OBJ_CACHE = {'requirements': {}}


class JobNumberParamType(click.ParamType):
    """Number of jobs click param type.

    This param type accepts ``auto`` or any positive integer (>0) as valid
    values.
    """

    name = 'job number'

    def convert(self, value, param, context):
        """Convert string ``auto`` into the CPU count."""
        if value.lower() == 'auto':
            return multiprocessing.cpu_count()
        value = int(value)
        if value <= 0:
            self.fail(
                '{0} is not a positive integer'.format(value), param, context)
        return value


JOB_NUMBER = JobNumberParamType()


def validate_key_value_option(ctx, param, value):
    """Validate an option that expects key=value formated values."""
    try:
        key, value = value.split('=', 1)
        return key, value
    except ValueError:
        raise click.BadParameter(
            '{} needs to be in format key=value'.format(param.name))


class RstParser():
    """A restructured text parser."""

    def _get_publisher(self, source):
        """Get docutils publisher."""
        extra_params = {
            'syntax_highlight': 'short',
            'input_encoding': 'utf-8',
            'embed_stylesheet': False,
        }
        pub = docutils.core.Publisher(
            source_class=docutils.io.StringInput,
            destination_class=docutils.io.StringOutput
        )
        pub.set_components('standalone', 'restructuredtext', 'html')
        pub.process_programmatic_settings(None, extra_params, None)
        pub.set_source(source=source)
        pub.publish(enable_exit_status=True)
        return pub

    def parse(self, source):
        """Parse restructured text."""
        pub = self._get_publisher(source)
        return pub.writer.parts.get('body')


RST_PARSER = RstParser()


def generate_test_id(test):
    """Generate the test_case_id as the Python import path.

    It could be either ``module.test_name`` or ``module.ClassName.test_name``
    if the test methods is defined within a class.

    :param test: a Testimony TestFunction instance.
    """
    test_case_id_parts = [
        test.testmodule.replace('/', '.').replace('.py', ''),
        test.name
    ]
    if test.parent_class is not None:
        test_case_id_parts.insert(-1, test.parent_class)
    return '.'.join(test_case_id_parts)


def load_custom_fields(custom_fields_opt):
    """Load the custom fields from the --custom-fields option.

    The --custom-fields option can receive either a string on the format
    ``key=value`` or a JSON string ``{"key":"value"}``, which will be loaded
    into a dictionary.

    If the value passed is not in JSON or key=value format it will be ignored.

    :param custom_fields_opt: A tuple of --custom-fields option.
    """
    custom_fields = {}
    if not custom_fields_opt:
        return custom_fields
    for item in custom_fields_opt:
        if item.startswith('{'):
            custom_fields.update(json.loads(item))
        elif '=' in item:
            key, value = item.split('=', 1)
            custom_fields[key.strip()] = value.strip()
    return custom_fields


def map_steps(steps, expectedresults):
    """Map each step to its expected result.

    For example a docstring like::

        '''My test

        @steps:

        1. First step
        2. Second step
        3. Third step

        @expectedresults:

        1. First step expected result.
        2. Second step expected result.
        3. Third step expected result.
        '''

    Will produce a return like::

        [
            ('First step', 'First step expected result.'),
            ('Second step', 'Second step expected result.'),
            ('Third step', 'Third step expected result.'),
        ]

    :param steps: unparsed string expected to contain either a list of steps or
        a single paragraph.
    :param expectedresults: unparsed string expected to contain either a
        list of expectedresults or a single paragraph.
    """
    steps = RST_PARSER.parse(steps)
    expectedresults = RST_PARSER.parse(expectedresults)
    try:
        if not type(steps) == str:
            steps = steps.encode('utf-8')
        parsed_steps = minidom.parseString(steps)
        if not type(expectedresults) == str:
            expectedresults = expectedresults.encode('utf-8')
        parsed_expectedresults = minidom.parseString(expectedresults)
    except ExpatError:
        return [(steps, expectedresults)]
    if (parsed_steps.firstChild.tagName == 'p' and
            parsed_expectedresults.firstChild.tagName == 'p'):
        parsed_steps = [parsed_steps.firstChild.toxml().decode('utf-8')]
        parsed_expectedresults = [
            parsed_expectedresults.firstChild.toxml().decode('utf-8')]
    elif (parsed_steps.firstChild.tagName == 'ol' and
            parsed_expectedresults.firstChild.tagName == 'ol'):
        parsed_steps = [
            u'<p>{}</p>'.format(element.firstChild.toxml().decode('utf-8'))
            for element in parsed_steps.getElementsByTagName('li')
        ]
        parsed_expectedresults = [
            u'<p>{}</p>'.format(element.firstChild.toxml().decode('utf-8'))
            for element in parsed_expectedresults.getElementsByTagName('li')
        ]
    else:
        parsed_steps = [steps]
        parsed_expectedresults = [expectedresults]
    if len(parsed_steps) == len(parsed_expectedresults):
        return zip(parsed_steps, parsed_expectedresults)
    else:
        return [(steps, expectedresults)]


def generate_test_steps(steps_map):
    """Generate a new TestSteps object.

    Fill the steps information with the `steps_map` values.

    :param steps_map: a list of tuples mapping to each step and
        its expected result.
    """
    test_steps = TestSteps()
    test_steps.keys = ['step', 'expectedResult']
    steps = []
    for item in steps_map:
        test_step = TestStep()
        test_step.values = list(item)
        steps.append(test_step)
    test_steps.steps = steps
    return test_steps


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
    """Return the summary of test results by their status.

    :param test_results: A list of dicts with information about
        test results, such as those reported in a jUnit file.
    :return: A dictionary containing a summary for all test results
        provided by the ``test_results`` parameter, broken down by their
        status.
    """
    return Counter([test['status'] for test in test_results])


def fetch_requirement(query, project, collect_only=False):
    """Fetch or create a requirement.

    Return the fetched or created requirement object.
    """
    click.echo(
        'Fetching requirement {0}.'.format(query))
    if query in OBJ_CACHE['requirements'].keys():
        return OBJ_CACHE['requirements'][query]
    requirement = None
    if not collect_only:
        results = Requirement.query(
            query,
            fields=['title', 'work_item_id']
        )
        if len(results) > 0:
            # As currently is not possible to get a single
            # match for the title, make sure to not use a
            # not intended Requirement.
            for result in results:
                if result.title == query or result.work_item_id == query:
                    requirement = result
    if requirement is None:
        click.echo(
            'Creating requirement {0}.'.format(query))
        if not collect_only:
            requirement = Requirement.create(
                project,
                query,
                '',
                reqtype='functional'
            )
            requirement.status = 'approved'
            requirement.update()
    if query not in OBJ_CACHE['requirements'].keys():
        OBJ_CACHE['requirements'][query] = requirement
    return requirement


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

    for test in tests:
        # Fetch the test case id if the @Id tag is present otherwise generate a
        # test_case_id based on the test Python import path
        test_case_id = test.tokens.get('id', generate_test_id(test))
        if test.docstring:
            if not type(test.docstring) == unicode:
                test.docstring = test.docstring.decode('utf8')

        # Is the test automated? Acceptable values are:
        # automated, manualonly, and notautomated
        auto_status = test.tokens.get(
            'caseautomation',
            'notautomated' if test.tokens.get('status') else 'automated'
        ).lower()
        caseposneg = test.tokens.get(
            'caseposneg',
            'negative' if 'negative' in test.name else 'positive'
        ).lower()
        subtype1 = test.tokens.get(
            'subtype1',
            '-'
        ).lower()
        casecomponent = test.tokens.get('casecomponent', '-').lower()
        caseimportance = test.tokens.get(
            'caseimportance', 'medium').lower()
        caselevel = test.tokens.get('caselevel', 'component').lower()
        description = test.tokens.get(
            'description', test.docstring if test.docstring else '')
        description = RST_PARSER.parse(description)
        setup = test.tokens.get('setup')
        status = test.tokens.get('status', 'approved').lower()
        testtype = test.tokens.get(
            'testtype',
            'functional'
        ).lower()
        title = test.tokens.get('title', test.name)
        upstream = test.tokens.get('upstream', 'no').lower()
        steps = test.tokens.get('steps')
        expectedresults = test.tokens.get('expectedresults')

        if steps and expectedresults:
            test_steps = generate_test_steps(
                map_steps(steps, expectedresults))
        else:
            test_steps = None

        results = []
        if not collect_only:
            results = TestCase.query(
                test_case_id,
                fields=[
                    'caseautomation',
                    'caseposneg',
                    'description',
                    'work_item_id'
                ]
            )
        requirement_name = test.tokens.get(
            'requirement', parse_requirement_name(path))
        if len(results) == 0:
            click.echo(
                'Creating test case {0} for requirement: {1}.'
                .format(title, requirement_name)
            )
            if not collect_only:
                test_case = TestCase.create(
                    project,
                    title,
                    description,
                    caseautomation=auto_status,
                    casecomponent=casecomponent,
                    caseimportance=caseimportance,
                    caselevel=caselevel,
                    caseposneg=caseposneg,
                    setup=setup,
                    subtype1=subtype1,
                    test_case_id=test_case_id,
                    testtype=testtype,
                    upstream=upstream,
                )
                test_case.status = status
                if test_steps:
                    test_case.test_steps = test_steps
                test_case.update()
            click.echo(
                'Linking test case {0} to requirement: {1}.'
                .format(title, requirement_name)
            )
            if not collect_only:
                requirement = fetch_requirement(
                    requirement_name, project, collect_only)
                test_case.add_linked_item(
                    requirement.work_item_id, 'verifies')
        else:
            click.echo(
                'Updating test case {0} for requirement {1}.'
                .format(title, requirement_name)
            )
            # Ensure that a single match for the Test Case is
            # returned.
            assert len(results) == 1
            test_case = results[0]
            if not collect_only and any((
                    test_case.caseautomation != auto_status,
                    test_case.casecomponent != casecomponent,
                    test_case.caseimportance != caseimportance,
                    test_case.caselevel != caselevel,
                    test_case.caseposneg != caseposneg,
                    test_case.description != description,
                    test_case.setup != setup,
                    test_case.status != status,
                    test_case.subtype1 != subtype1,
                    test_case.test_steps != test_steps,
                    test_case.testtype != testtype,
                    test_case.title != title,
                    test_case.upstream != upstream,
            )):
                test_case.caseautomation = auto_status
                test_case.casecomponent = casecomponent
                test_case.caseimportance = caseimportance
                test_case.caselevel = caselevel
                test_case.caseposneg = caseposneg
                test_case.description = description
                test_case.setup = setup
                test_case.status = status
                test_case.subtype1 = subtype1
                test_case.testtype = testtype
                test_case.title = title
                test_case.upstream = upstream
                if test_steps:
                    test_case.test_steps = test_steps
                test_case.update()


def add_test_record(result):
    """Task that adds a test result to a test run.

    This task relies on ``OBJ_CACHE`` to get the test run and user objects. The
    object cache is needed since suds objects are not able to be pickled and it
    is not possible to pass them to processes.
    """
    test_run = OBJ_CACHE['test_run']
    user = OBJ_CACHE['user']
    testcases = OBJ_CACHE['testcases']
    junit_test_case_id = '{0}.{1}'.format(result['classname'], result['name'])
    test_case_id = testcases.get(junit_test_case_id)
    if not test_case_id:
        click.echo(
            'Missing ID information for test {0}, using junit test case id...'
            .format(junit_test_case_id)
        )
        test_case_id = junit_test_case_id
    test_case = TestCase.query(test_case_id)
    if len(test_case) == 0:
        click.echo(
            'Was not able to find test case {0} with id {1}, skipping...'
            .format(junit_test_case_id, test_case_id)
        )
        return
    status = POLARION_STATUS[result['status']]
    work_item_id = test_case[0].work_item_id
    click.echo(
        'Adding test record for test case {0} with status {1}.'
        .format(work_item_id, status)
    )
    message = result.get('message', '')
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
    except Exception as err:
        click.echo(
            'Error when adding test record for "{test_case_id}" with the '
            'following information:\n'
            'duration="{duration}"'
            'executed="{executed}"\n'
            'executed_by="{executed_by}"\n'
            'test_result="{test_result}"\n'
            'test_comment="{test_comment}"\n'
            .format(
                test_case_id=work_item_id,
                test_result=status,
                test_comment=message,
                executed_by=user,
                executed=datetime.datetime.now(),
                duration=float(result.get('time', '0'))
            )
        )
        click.echo(traceback.format_exc(), err=True)
        raise


@click.group()
@click.option(
    '--jobs',
    '-j',
    default='1',
    help='Number of jobs or auto to use the CPU count.',
    type=JOB_NUMBER
)
@click.option(
    '--token-prefix',
    callback=_validate_token_prefix,
    default=':',
    help='Single character to prefix a token.'
)
@click.pass_context
def cli(context, jobs, token_prefix):
    """Betelgeuse CLI command group."""
    context.obj = {}
    context.obj['jobs'] = jobs
    # Configure Testimony tokens
    testimony.SETTINGS['tokens'] = [
        'caseautomation',
        'casecomponent',
        'caseimportance',
        'caselevel',
        'caseposneg',
        'assert',
        'description',
        'expectedresults',
        'id',
        'requirement',
        'setup',
        'steps',
        'subtype1',
        'testtype',
        'upstream',
        'title',
    ]
    testimony.SETTINGS['minimum_tokens'] = ['id']
    testimony.SETTINGS['token_prefix'] = token_prefix


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
    pool = multiprocessing.Pool(context.obj['jobs'])
    pool.map(add_test_case, testcases.items())
    pool.close()
    pool.join()


@cli.command('test-plan')
@click.option(
    '--name',
    default='test-plan-{0}'.format(time.time()),
    help='Name for new Test Plan.',
)
@click.option(
    '--plan-type',
    default='release',
    help='Test Plans can be Releases or Iterations.',
    type=click.Choice([
        'release',
        'iteration',
    ])
)
@click.option(
    '--parent-name',
    help='Name of parent Test Plan to link to.',
)
@click.option(
    '--custom-fields',
    help='Custom fields for the test plan.',
    multiple=True,
)
@click.argument('project')
@click.pass_context
def test_plan(context, name, plan_type, parent_name, custom_fields, project):
    """Create a new test plan in Polarion."""
    # Sanitize names to valid values for IDs...
    custom_fields = load_custom_fields(custom_fields)
    plan_id = re.sub(INVALID_CHARS_REGEX, '_', name).replace(' ', '_')
    parent_plan_id = (
        re.sub(INVALID_CHARS_REGEX, '_', parent_name).replace(' ', '_')
        if parent_name else parent_name
    )
    # Check if the test plan already exists
    result = Plan.search('id:{0}'.format(plan_id))
    if len(result) == 1:
        click.echo('Found Test Plan {0}.'.format(name))
        test_plan = result[0]
    else:
        # Unlike Testrun, Pylarion currently does not accept **kwargs in
        # Plan.create() so the custom fields need to be updated after the
        # creation
        test_plan = Plan.create(
            parent_id=parent_plan_id,
            plan_id=plan_id,
            plan_name=name,
            project_id=project,
            template_id=plan_type
        )
        click.echo(
            'Created new Test Plan {0} with ID {1}.'.format(name, plan_id))

    update = False
    for field, value in custom_fields.items():
        if getattr(test_plan, field) != value:
            setattr(test_plan, field, value)
            click.echo(
                'Test Plan {0} updated with {1}={2}.'.format(
                    test_plan.name, field, value)
            )
            update = True
    if update:
        test_plan.update()


@cli.command('test-results')
@click.option(
    '--path',
    default='junit-results.xml',
    help='Path to the jUnit XML file.',
    type=click.Path(exists=True, dir_okay=False),
)
def test_results(path):
    """Summary of tests from the jUnit XML file."""
    test_summary = parse_test_results(parse_junit(path))
    summary = '\n'.join(
        ['{0}: {1}'.format(*status) for status in test_summary.items()]
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
    '--source-code-path',
    help='Path to the source code for the jUnit results.',
    type=click.Path(exists=True),
)
@click.option(
    '--test-run-id',
    default='test-run-{0}'.format(time.time()),
    help='Test Run ID to be created/updated.',
)
@click.option(
    '--test-run-type',
    default='buildacceptance',
    help='Test Run Type.',
    type=click.Choice([
        'buildacceptance',
        'regression',
        'featureverification',
    ])
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
@click.option(
    '--custom-fields',
    help='Custom fields to be passed when creating a new test run.',
    multiple=True,
)
@click.argument('project')
@click.pass_context
def test_run(
        context, path, source_code_path, test_run_id, test_run_type,
        test_template_id, user, custom_fields, project):
    """Execute a test run based on jUnit XML file."""
    custom_fields = load_custom_fields(custom_fields)
    test_run_id = re.sub(INVALID_CHARS_REGEX, '', test_run_id)
    testcases = {
        generate_test_id(test): test.tokens.get('id')
        for test in itertools.chain(
                *testimony.get_testcases([source_code_path]).values()
        )
    }
    results = parse_junit(path)
    try:
        test_run = TestRun(test_run_id, project_id=project)
        click.echo('Test run {0} found.'.format(test_run_id))
    except PylarionLibException as err:
        click.echo(err, err=True)
        click.echo('Creating test run {0}.'.format(test_run_id))
        test_run = TestRun.create(
            project, test_run_id, test_template_id, type=test_run_type,
            **custom_fields)

    update = False
    if test_run.type != test_run_type:
        test_run.type = test_run_type
        update = True
    for field, value in custom_fields.items():
        if getattr(test_run, field) != value:
            setattr(test_run, field, value)
            click.echo(
                'Test Run {0} updated with {1}={2}.'.format(
                    test_run_id, field, value)
            )
            update = True
    if update:
        test_run.update()

    OBJ_CACHE['test_run'] = test_run
    OBJ_CACHE['user'] = user
    OBJ_CACHE['testcases'] = testcases

    TestRun.session.tx_begin()
    pool = multiprocessing.Pool(context.obj['jobs'])
    pool.map(add_test_record, results)
    pool.close()
    pool.join()
    TestRun.session.tx_commit()


def create_xml_property(name, value):
    """Create an XML property element and set its name and value attributes."""
    element = ElementTree.Element('property')
    element.set('name', name)
    element.set('value', value)
    return element


@cli.command('xml-test-run')
@click.option(
    '--custom-fields',
    help='Indicates to the importer which custom fields should be set. '
    'Expected format is either id=value or JSON format {"id":"value"}. This '
    'option can be specified multiple times.',
    multiple=True,
)
@click.option(
    '--dry-run',
    help='Indicate to the importer to not make any change.',
    is_flag=True,
)
@click.option(
    '--lookup-method',
    default='custom',
    help='Indicates to the importer which lookup method to use. "id" for work '
    'item id or "custom" for custom id (default).',
    type=click.Choice([
        'id',
        'custom',
    ])
)
@click.option(
    '--no-include-skipped',
    help='Specify to make the importer not import skipped tests.',
    is_flag=True,
)
@click.option(
    '--response-property',
    callback=validate_key_value_option,
    help='When defined, the impoter will mark all responses with the selector.'
    'The format is "--response-property property_key=property_value".',
)
@click.option(
    '--status',
    default='finished',
    help='Define which status the test run should be set: "Finished" (default)'
    'or "In Progress"',
    type=click.Choice([
        'finished',
        'inprogress',
    ])
)
@click.option(
    '--test-run-id',
    default='test-run-{0}'.format(time.time()),
    help='Test Run ID to be created/updated.',
)
@click.option(
    '--test-run-title',
    help='Test Run title.',
)
@click.argument('junit-path', type=click.Path(exists=True, dir_okay=False))
@click.argument('source-code-path', type=click.Path(exists=True))
@click.argument('user')
@click.argument('project')
@click.argument('output-path')
@click.pass_context
def xml_test_run(
        context, custom_fields, dry_run, lookup_method, no_include_skipped,
        response_property, status, test_run_id, test_run_title, junit_path,
        source_code_path, user, project, output_path):
    """Generate an XML suited to be importer by the test-run importer.

    This will read the jUnit XML at JUNIT_PATH and the source code at
    SOURCE_CODE_PATH in order to generate a XML file place at OUTPUT_PATH. The
    generated XML file will be ready to be imported by the XML Test Run
    Importer.

    The test run will be created on the project ID provided by PROJECT and
    will be assigned to the Polarion user ID provided by USER.

    Other test run options can be set by the various options this command
    accepts. Check their help for more information.
    """
    test_run_id = re.sub(INVALID_CHARS_REGEX, '', test_run_id)
    testsuites = ElementTree.Element('testsuites')
    properties = ElementTree.Element('properties')
    custom_fields = load_custom_fields(custom_fields)
    custom_fields.update({
        'polarion-dry-run':
            'true' if dry_run else 'false',
        'polarion-include-skipped':
            'false' if no_include_skipped else 'true',
        'polarion-set-testrun-finished':
            'false' if status == 'inprogress' else 'true',
    })
    if response_property:
        key = 'polarion-response-' + response_property[0]
        custom_fields[key] = response_property[1]
    custom_fields['polarion-lookup-method'] = lookup_method
    custom_fields['polarion-project-id'] = project
    custom_fields['polarion-testrun-id'] = test_run_id
    if test_run_title:
        custom_fields['polarion-testrun-title'] = test_run_title
    custom_fields['polarion-user-id'] = user
    properties_names = (
        'polarion-dry-run',
        'polarion-include-skipped',
        'polarion-lookup-method',
        'polarion-project-id',
        'polarion-set-testrun-finished',
        'polarion-testrun-id',
        'polarion-testrun-title',
        'polarion-user-id',
    )
    for name, value in custom_fields.items():
        if (not name.startswith('polarion-custom-') and
                not name.startswith('polarion-response-') and
                name not in properties_names):
            name = 'polarion-custom-{}'.format(name)
        properties.append(create_xml_property(name, value))
    testsuites.append(properties)

    testcases = {
        generate_test_id(test): test.tokens.get('id')
        for test in itertools.chain(
                *testimony.get_testcases([source_code_path]).values()
        )
    }
    testsuite = ElementTree.parse(junit_path).getroot()

    # XML importer expects skipped instead of the xUnit testsuite skips attr
    if 'skips' in testsuite.attrib:
        testsuite.attrib['skipped'] = testsuite.attrib['skips']
        del testsuite.attrib['skips']
    for testcase in testsuite.iterfind('testcase'):
        # XML importer does not accept some xUnit testcase attributes
        if 'file' in testcase.attrib:
            del testcase.attrib['file']
        if 'line' in testcase.attrib:
            del testcase.attrib['line']
        junit_test_case_id = '{0}.{1}'.format(
            testcase.get('classname'), testcase.get('name'))
        test_case_id = testcases.get(junit_test_case_id)
        if not test_case_id:
            click.echo(
                'Could not find ID information for {}, skipping...'
                .format(junit_test_case_id)
            )
            continue
        test_properties = ElementTree.Element('properties')
        element = ElementTree.Element('property')
        element.set('name', 'polarion-testcase-id')
        element.set('value', test_case_id)
        test_properties.append(element)
        testcase.append(test_properties)
    testsuites.append(testsuite)

    et = ElementTree.ElementTree(testsuites)
    et.write(output_path, encoding='utf-8', xml_declaration=True)
