"""Betelgeuse.

Betelgeuse reads standard Python test cases and offers tools to interact with
Polarion. Possible interactions:

* Automatic creation of Requirements and Test Cases from a Python
  project code base and jUnit XML file.
* Synchronization of Test Cases from a Python project code base
  and jUnit XML file.
* Creation of Test Runs based on a jUnit XML file.
"""
import itertools
import json
import logging
import re
import ssl
import time
import warnings
from collections import Counter
from xml.dom import minidom
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError

import click
from pylarion.plan import Plan
from pylarion.work_item import Requirement

from betelgeuse import collector, config, parser


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


def validate_key_value_option(ctx, param, value):
    """Validate an option that expects key=value formated values."""
    if value is None:
        return
    try:
        key, value = value.split('=', 1)
        return key, value
    except ValueError:
        raise click.BadParameter(
            '{} needs to be in format key=value'.format(param.name))


def generate_test_id(test):
    """Generate the test_case_id as the Python import path.

    It could be either ``module.test_name`` or ``module.ClassName.test_name``
    if the test methods is defined within a class.

    :param test: a ``collector.TestFunction`` instance.
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

        :steps:

            1. First step
            2. Second step
            3. Third step

        :expectedresults:

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
    try:
        parsed_steps = minidom.parseString(steps.encode('utf-8'))
        parsed_expectedresults = minidom.parseString(
            expectedresults.encode('utf-8'))
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
            element.firstChild.toxml().decode('utf-8')
            for element in parsed_steps.getElementsByTagName('li')
        ]
        parsed_expectedresults = [
            element.firstChild.toxml().decode('utf-8')
            for element in parsed_expectedresults.getElementsByTagName('li')
        ]
    else:
        parsed_steps = [steps]
        parsed_expectedresults = [expectedresults]
    if len(parsed_steps) == len(parsed_expectedresults):
        return zip(parsed_steps, parsed_expectedresults)
    else:
        return [(steps, expectedresults)]


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


class AliasedGroup(click.Group):
    """Make xml-<command> commands resolve to <command>."""

    def get_command(self, ctx, cmd_name):
        """Drop xml- prefix when getting the command."""
        if cmd_name in ('xml-test-case', 'xml-test-run'):
            new_cmd_name = cmd_name.lstrip('xml-')
            warnings.warn(
                'The command {} is renamed to {}, this alias will be removed '
                'in a future version of Betelgeuse'
                .format(cmd_name, new_cmd_name),
                DeprecationWarning,
                stacklevel=2
            )
            cmd_name = new_cmd_name
        return super(AliasedGroup, self).get_command(ctx, cmd_name)


pass_config = click.make_pass_decorator(config.BetelgeuseConfig, ensure=True)


@click.group(cls=AliasedGroup)
@click.option(
    '--config-module',
    envvar='BETELGEUSE_CONFIG_MODULE'
)
@click.pass_context
def cli(ctx, config_module):
    """Betelgeuse CLI command group."""
    ctx.obj = config.BetelgeuseConfig(config_module)


@cli.command('requirement')
@click.argument('source-code-path', type=click.Path(exists=True))
@click.argument('project')
def requirement(source_code_path, project):
    """Create and/or update requirements in Polarion."""
    requirements = []
    source_testcases = itertools.chain(
        *collector.collect_tests(source_code_path).values())
    for testcase in source_testcases:
        fields = {k.lower(): v for k, v in testcase.fields.items()}
        if ('requirement' in fields and
                fields['requirement'] not in requirements):
            requirement_title = fields['requirement']
            results = Requirement.query(
                requirement_title,
                fields=['status', 'title']
            )
            requirement = None
            for result in results:
                if result.title == requirement_title:
                    requirement = result
                    break
            if requirement is None:
                click.echo(
                    u'Creating requirement {0}.'.format(fields['requirement'])
                )
                requirement = Requirement.create(
                    project,
                    requirement_title,
                    '',
                    reqtype='functional'
                )
            if requirement.status != 'approved':
                click.echo(
                    u'Approving requirement {0}.'.format(requirement.title)
                )
                requirement.status = 'approved'
                requirement.update()


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
def test_plan(name, plan_type, parent_name, custom_fields, project):
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


def create_xml_property(name, value):
    """Create an XML property element and set its name and value attributes."""
    element = ElementTree.Element('property')
    element.set('name', name)
    element.set('value', value)
    return element


def create_xml_testcase(config, testcase, automation_script_format):
    """Create an XML testcase element.

    The element will be in the format to be used by the XML test case importer.
    """
    testcase.fields = {k.lower(): v for k, v in testcase.fields.items()}
    fields = testcase.fields.copy()
    element = ElementTree.Element('testcase')
    element.set('id', fields.pop('id', generate_test_id(testcase)))
    # TODO: set other attributes assignee-id, due-date, initial-estimate
    if testcase.docstring:
        if not type(testcase.docstring) == unicode:
            testcase.docstring = testcase.docstring.decode('utf8')

    title = fields.get('title')
    if title is None:
        default = getattr(config, 'DEFAULT_TITLE_VALUE', None)
        if callable(default):
            default = default(testcase)
        if default is not None:
            fields['title'] = default
    title = ElementTree.Element('title')
    title.text = fields['title']
    element.append(title)
    fields['description'] = fields.get(
        'description',
        parser.parse_rst(testcase.docstring)
    )
    description = ElementTree.Element('description')
    description.text = fields.pop('description')
    element.append(description)

    if 'requirement' in fields:
        linked_work_items = ElementTree.Element('linked-work-items')
        linked_work_item = ElementTree.Element('linked-work-item')
        linked_work_item.set('workitem-id', fields.pop('requirement'))
        linked_work_item.set('role-id', 'verifies')
        linked_work_item.set('lookup-method', 'name')
        linked_work_items.append(linked_work_item)
        element.append(linked_work_items)

    steps = fields.pop('steps', None)
    expectedresults = fields.pop('expectedresults', None)

    if steps and expectedresults:
        test_steps = ElementTree.Element('test-steps')
        for step, expectedresult in map_steps(steps, expectedresults):
            test_step = ElementTree.Element('test-step')
            test_step_column = ElementTree.Element('test-step-column')
            test_step_column.set('id', 'step')
            test_step_column.text = step
            test_step.append(test_step_column)
            test_step_column = ElementTree.Element('test-step-column')
            test_step_column.set('id', 'expectedResult')
            test_step_column.text = expectedresult
            test_step.append(test_step_column)
            test_steps.append(test_step)
        element.append(test_steps)

    custom_fields = ElementTree.Element('custom-fields')
    for field in config.TESTCASE_CUSTOM_FIELDS:
        value = fields.get(field)
        if value is None:
            default = getattr(
                config, 'DEFAULT_{}_VALUE'.format(field.upper()), None)
            if callable(default):
                default = default(testcase)
            if default is not None:
                fields[field] = default
                testcase.fields[field] = default

    for field in fields.keys():
        transform_func = getattr(
            config, 'TRANSFORM_{}_VALUE'.format(field.upper()), None)
        if callable(transform_func):
            fields[field] = transform_func(fields[field], testcase)

    fields['automation_script'] = automation_script_format.format(
        path=testcase.module_def.path,
        line_number=testcase.function_def.lineno,
    )

    for key, value in fields.items():
        if value is None or key not in config.TESTCASE_CUSTOM_FIELDS:
            continue
        custom_field = ElementTree.Element('custom-field')
        custom_field.set('id', key)
        custom_field.set('content', value)
        custom_fields.append(custom_field)
    element.append(custom_fields)
    return element


@cli.command('test-case')
@click.option(
    '--automation-script-format',
    help=(r'The format for the automation-script field. The variables {path} '
          'and {line_number} are available and will be expanded to the test '
          'case module path and the line number where it\'s defined '
          'respectively. Default: {path}#{line_number}'),
    default='{path}#{line_number}',
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
    'item id, "custom" for custom id (default) or "name" for test case '
    'title.',
    type=click.Choice([
        'custom',
        'id',
        'name',
    ])
)
@click.option(
    '--response-property',
    callback=validate_key_value_option,
    help='When defined, the impoter will mark all responses with the selector.'
    'The format is "--response-property property_key=property_value".',
)
@click.argument('source-code-path', type=click.Path(exists=True))
@click.argument('project')
@click.argument('output-path')
@pass_config
def test_case(
        config, automation_script_format, dry_run, lookup_method,
        response_property, source_code_path, project, output_path):
    """Generate an XML suited to be importer by the test-case importer.

    This will read the source code at SOURCE_CODE_PATH in order to capture the
    test cases and generate a XML file place at OUTPUT_PATH. The generated XML
    file will be ready to be imported by the XML Test Case Importer.

    The test cases will be created on the project ID provided by PROJECT and
    will be assigned to the Polarion user ID provided by USER.

    Other test case importer options can be set by the various options this
    command accepts. Check their help for more information.
    """
    testcases = ElementTree.Element('testcases')
    testcases.set('project-id', project)
    if response_property:
        response_properties = ElementTree.Element('response-properties')
        element = ElementTree.Element('response-property')
        element.set('name', response_property[0])
        element.set('value', response_property[1])
        response_properties.append(element)
        testcases.append(response_properties)
    properties = ElementTree.Element('properties')
    properties.append(create_xml_property(
        'dry-run', 'true' if dry_run else 'false'))
    properties.append(create_xml_property(
        'lookup-method', lookup_method))
    testcases.append(properties)

    source_testcases = itertools.chain(
        *collector.collect_tests(source_code_path).values())
    for testcase in source_testcases:
        testcases.append(
            create_xml_testcase(config, testcase, automation_script_format))

    et = ElementTree.ElementTree(testcases)
    et.write(output_path, encoding='utf-8', xml_declaration=True)


@cli.command('test-run')
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
    '--test-run-template-id',
    help='Test Run template ID.'
)
@click.option(
    '--test-run-title',
    help='Test Run title.',
)
@click.option(
    '--test-run-type-id',
    help='Test Run type ID.'
)
@click.argument('junit-path', type=click.Path(exists=True, dir_okay=False))
@click.argument('source-code-path', type=click.Path(exists=True))
@click.argument('user')
@click.argument('project')
@click.argument('output-path')
def test_run(
        custom_fields, dry_run, lookup_method, no_include_skipped,
        response_property, status, test_run_id, test_run_template_id,
        test_run_title, test_run_type_id, junit_path, source_code_path, user,
        project, output_path):
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
    if test_run_template_id:
        custom_fields['polarion-testrun-template-id'] = test_run_template_id
    if test_run_title:
        custom_fields['polarion-testrun-title'] = test_run_title
    if test_run_type_id:
        custom_fields['polarion-testrun-type-id'] = test_run_type_id
    custom_fields['polarion-user-id'] = user
    properties_names = (
        'polarion-dry-run',
        'polarion-include-skipped',
        'polarion-lookup-method',
        'polarion-project-id',
        'polarion-set-testrun-finished',
        'polarion-testrun-id',
        'polarion-testrun-template-id',
        'polarion-testrun-title',
        'polarion-testrun-type-id',
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
        generate_test_id(test): test.fields.get('id')
        for test in itertools.chain(
                *collector.collect_tests(source_code_path).values()
        )
    }
    testsuite = ElementTree.parse(junit_path).getroot()

    for testcase in testsuite.iterfind('testcase'):
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
