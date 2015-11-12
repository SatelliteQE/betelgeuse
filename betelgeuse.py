"""Betelgeuse

Betelgeuse reads standard Python test cases and offers tools to interact with
Polarion. Possible interactions:

* Automatic creation of Requirements and Test Cases from a Python
  project code base and jUnit XML file.
* Synchronization of Test Cases from a Python project code base
  and jUnit XML file.
* Creation of Test Runs based on a jUnit XML file.
"""
import click
import ssl
import testimony

from pylarion.work_item import TestCase, Requirement

# Avoid SSL errors
ssl._create_default_https_context = ssl._create_unverified_context


def parse_requirement_name(test_case_id):
    """Return the Requirement name for a given test_case_id."""
    index = -2
    parts = test_case_id.split('.')
    if parts[index][0].isupper():
        index -= 1
    return parts[index].replace('test_', '').replace('_', ' ').title()


@click.command()
@click.option(
    '--path',
    default='tests',
    help='Path to the tests directories.',
    type=click.Path(exists=True, file_okay=False),
)
@click.option(
    '--collect-only',
    help=('Not perform any operation on Polarion, just prints '
          'collected information.'),
    is_flag=True,
)
@click.argument('project')
def cli(path, collect_only, project):
    """Betelgeuse reads standard Python test cases and offers
    tools to interact with Polarion.
    """
    testcases = testimony.get_testcases([path])
    for path, tests in testcases.items()[:1]:
        requirement = None
        for test in tests:
            test_case_id = '{0}.{1}.{2}'.format(
                path.replace('/', '.').replace('.py', ''),
                test.parent_class,
                test.name
            )
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
                    'Liking test case {0} to verify requirement {1}.'
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
