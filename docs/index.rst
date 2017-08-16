========================
Betelgeuse documentation
========================

.. contents:: Topics
    :local:


What is Betelgeuse?
===================

Betelgeuse is a python program that reads standard Python test cases and offers
tools to interact with Polarion. Possible interactions are:

* Automatic creation/update of Requirements and Test Cases from a Python
  project code base.
* Automatic creation/update of Test Runs based on a jUnit XML file.

Betelgeuse uses Pylarion project to communicate with Polarion.

Prerequisites
=============

Login to Polarion in a browser to check if the login user has permissions to
create/update the following entities in Polarion:

* requirement
* test case
* test run

If you want Betelgeuse to automatically approve the test cases, then make sure
the user has permission to approve them. Betelgeuse will check if the user is
on the allowed approvers list, and, if that is the case, will set the approvee
and approve the test case.

Quick Start
===========

1. Betelgeuse uses Pylarion to interact with Polarion. Install Pylarion from its
   source.

   .. note::

     - It may be possible that the latest version of Betelgeuse may not work
       correctly with some versions of Pylarion. In this case, please use an
       alternate working version of Pylarion.
     - Read Pylarion documentation and set up ``.pylarion`` config file as
       required.

2. Install betelguese from pypi.

   .. code-block:: console

       $ pip install betelgeuse

3. Alternatively you can install from source:

   .. code-block:: console

       $ git clone https://github.com/SatelliteQE/betelgeuse.git
       $ cd betelgeuse
       $ pip install -e .

   .. note:: It is always recommended to use python virtual environment

How it works?
=============

Assuming that you have a ``test_user.py`` file with the following content:

.. code-block:: python

    import entities
    import unittest


    class EntitiesTest(unittest.TestCase):

        def test_positive_create_user(self):
            user = entities.User(name='David', age=20)
            self.assertEqual(user.name, 'David')
            self.assertEqual(user.age, 20)

        def test_positive_create_car(self):
            car = entities.Car(make='Honda', year=2016)
            self.assertEqual(car.make, 'Honda')
            self.assertEqual(car.year, 2016)

Using the example above, Betelgeuse will recognize that there are 2 test cases
available, and the following attributes will be derived:

* Title: this attribute will be derived from the name of the test method itself:

      - test_positive_create_user
      - test_positive_create_car

* ID: this attribute will be derived from the concatenation of the
  *module.test_name* or *module.ClassName.test_name* if the test method is
  defined within a class. In other words, *the Python import path* will be used
  to derived the ID. Using our example, the values generated would be:

      - test_user.EntitiesTest.test_positive_create_user
      - test_user.EntitiesTest.test_positive_create_car

By default, the values automatically derived by Betelgeuse are not very
flexible, specially in the case when you rename an existing test case or move
it to a different class or module. It is recommended, therefore, the use of
field list fields to provide a bit more information about the tests.

.. code-block:: python

      import entities
      import unittest


      class EntitiesTest(unittest.TestCase):

          def test_positive_create_user(self):
              """Create a new user providing all expected attributes.

              :id: 1d73b8cc-a754-4637-8bae-d9d2aaf89003
              :title: Create a new user providing all expected attributes
              """
              user = entities.User(name='David', age=20)
              self.assertEqual(user.name, 'David')
              self.assertEqual(user.age, 20)

Now Betelgeuse can use the ``:title:`` field to derive a friendlier name for
your test (instead of using *test_positive_create_user*) and a specific value
for its ID. Other information can also be added to the docstring to provide
more information, and this can be handled by adding more fields (named after
Polarion fields and custom fields).

.. note::

    1. Make sure that your ``IDs`` are indeed unique per test case.
    2. You can generate a unique UUID using the following code snippet.

       .. code-block :: python

           import uuid
           uuid.uuid4()

How steps and expectedresults work together
-------------------------------------------

Betelgeuse will look for some fields when parsing the test cases but there is
an special case: when both ``steps`` and ``expectedresults`` are defined
together.

Betelgeuse will try to match both and create paired step with an expected
result. For example in the following docstring:

.. code-block:: python

    """Create a new user providing all expected attributes.

    :id: 1d73b8cc-a754-4637-8bae-d9d2aaf89003
    :steps: Create an user with name and email
    :expectedresults: User is created without any error being raised
    """

A pair of ``Create an user with name and email`` step with ``User is created
without any error being raised`` expected result will be created. If multiple
steps and multiple expected is wanted, then a list can be used:

.. code-block:: python

    """Create a new user providing all expected attributes.

    :id: 1d73b8cc-a754-4637-8bae-d9d2aaf89003
    :steps:
        1. Open the user creation page
        2. Fill name and email
        3. Submit the form
    :expectedresults:
        1. A page with a form with name and email will be displayed
        2. The fields will be populated with the information filled in
        3. User is created without any error being raised
    """

On the above example three pairs will be created. The first will match the
first item on ``steps`` and first item on ``expectedresults``, the second pair
will be the second item on ``steps`` and the second item on
``expectedresults``, so on and so forth.

.. note::

    If the number of items are not the same, then only one pair will be
    created. The step will be the HTML generated by the value of ``steps`` and
    the expected result will be the HTML generate by the value of
    ``expectedresults``.

Usage Examples
==============

.. note::

  1. For easy understanding of Betelgeuse, this repository is already included with
  ``sample_project`` folder. This folder contains sample tests and XML results which
  will help in setting up and testing Betelgeuse for your project. The sample
  commands used below also use this data.

  2. Always run the test runner and Betelgeuse on the same directory to make
  sure that the test run ID mapping works fine. Otherwise Betelgeuse may
  report ID errors. More info can be found in `test-run command`_ section

help command
------------

.. code-block:: console

    $ betelgeuse --help

requirement command
-------------------

Creates/updates requirements in Polarion. This command will grab all
requirements (defined by the ``:requirement:`` field) and will create/update
them. Also it will approve the requirements which are not approved yet.

.. code-block:: console

    $ betelgeuse requirement sample_project/tests/ PROJECT_CLOUD

.. note::

    Requirements must be created in order to link test cases to them. Make sure
    to run this before importing the test cases.

test-case command
-----------------

The ``test-case`` command generates an XML file suited to be imported by the
Test Case XML Importer. It reads the Python test suite source code and
generates a XML file with all the information necessary for the Test Case XML
Importer.

The ``test-case`` command requires you to pass:

* The path to the Python test suite source code
* The Polarion project ID
* The output XML file path (it will override if the file already exists)

.. note::

    Even though ``--response-property`` is optional, it is highly recommended
    to pass it because will be easier to monitor the importer messages (which
    is not handled by Betelgeuse).

The example below shows how to run the command:

.. code-block:: console

    $ betelgeuse test-case \
        --automation-script-format "https://github.com/SatelliteQE/betelgeuse/tree/master/{path}#L{line_number}" \
        sample_project/tests \
        PROJECT \
        betelgeuse-test-cases.xml

test-plan command
-----------------

The test-plan command allows creating a parent or child test plans. This is
done by using --parent-name option.

Create a parent test plan
    If ``parent-name`` option is not specified, then just a parent test plan
    will be created.

Create a child test plan
    If ``parent-name`` option is specified, then a child test plan will be
    created and linked to the specified parent test plan.

Betelgeuse will automatically generate the test plan IDs from the passed test
plan names by replacing special characters and converting spaces to ``_``.

.. warning::

    Make sure to pass the right names for the test plans in order to find the
    expected work items in Polarion. Otherwise, you may see an error.

Examples:

.. code-block:: console

    $ betelgeuse test-plan --name "Parent Name" PROJECT_CLOUD
    Created new Test Plan Parent Name with ID Parent_Name.

    $ betelgeuse test-plan \
        --name "Child Name" \
        --parent-name "Parent Name" \
        PROJECT_CLOUD
    Created new Test Plan Child Name with ID Child_Name.

.. note::

    Use ``--plan-type`` to set the plan type of a test plan to ``release`` or
    ``iteration``. The default value is ``release``.

The test-plan command can also be used to update custom fields in a test plan.
The ``--custom-fields`` option can be used with a ``key=value`` format or a JSON
format as explained in `test-run command`_ section.

To create a new test plan and update its ``status``:

.. code-block:: console

    $ betelgeuse test-plan \
        --name="Iteration 1" \
        --custom-fields status=inprogress \
        PROJECT_CLOUD
    Created new Test Plan Iteration 1 with ID Iteration_1.
    Test Plan iteration 1 updated with status=inprogress.

The test-plan command is smart enough to check if a test plan with the given
name already exists before creating it.  For example, to update an already
existing test plan:

.. code-block:: console

    $ betelgeuse test-plan \
        --name="Iteration 1" \
        --custom-fields status=done \
        PROJECT_CLOUD
    Found Test Plan Iteration 1.
    Test Plan iteration 1 updated with status=done.

test-results command
--------------------

Gives a nice summary of test cases/results in the given jUnit XML file.

.. code-block:: console

    $ betelgeuse test-results --path \
    sample_project/results/sample-junit-result.xml

    Passed: 1

test-run command
----------------

The ``test-run`` command generates an XML file suited to be imported by the
Test Run XML importer. It takes:

* A valid xUnit XML file
* A Python test suite where test case IDs can be found

And generates a resulting XML file with all the information necessary for the
Test Run XML importer.

The ``test-run`` command only requires you to pass:

* The path to the xUnit XML file
* The path to the Python test suite source code
* The Polarion user ID
* The Polarion project ID
* The output XML file path (it will override if the file already exists)

.. note::

    Even though ``--response-property`` is optional, it is highly recommended
    to pass it because will be easier to monitor the importer messages (which
    is not handled by Betelgeuse).

The example below shows how to run ``test-run`` command:

.. code-block:: console

    $ betelgeuse test-run \
        --response-property property_key=property_value \
        sample_project/results/sample-junit-result.xml \
        sample_project/tests/ \
        testuser \
        PROJECT \
        betelgeuse-test-run.xml

Polarion custom fields can be set by using the ``--custom-fields`` option.
There are two ways to define custom fields:

``key=value`` format
    This a shortcut when you want to define plain strings as the value of a
    custom field.

JSON format
    This approach suits better when the type of the custom field matters. For
    example, if a custom field expects a boolean as a value.

Example using ``key=value`` format:

.. code-block:: console

    $ betelgeuse test-run \
        --custom-fields arch=x8664 \
        --custom-fields variant=server \
        --response-property property_key=property_value \
        sample_project/results/sample-junit-result.xml \
        sample_project/tests/ \
        testuser \
        PROJECT \
        betelgeuse-test-run.xml

Example using JSON format:

.. code-block:: console

    $ betelgeuse test-run \
        --custom-fields '{"isautomated":"true","arch":"x8664"}' \
        --response-property property_key=property_value \
        sample_project/results/sample-junit-result.xml \
        sample_project/tests/ \
        testuser \
        PROJECT \
        betelgeuse-test-run.xml

.. warning::

    Make sure to pass the the custom field ID (same as in Polarion) and its
    value. Also, pass custom field values as string since they will be
    converted to XML where there is no type information.

xml-test-case command
---------------------

Alias to the `test-case command`_.

.. warning::

    This alias is deprecated and will be removed on a future version.

xml-test-run command
--------------------

Alias to the `test-run command`_.

.. warning::

    This alias is deprecated and will be removed on a future version.

Case Study - A real world sample Test Case
===========================================

Field list fields can be used to provide more information about a test case.
The more information one provides via these fields, the more accurate the data
being imported into Polarion. For example:

.. code-block:: python

  import entities
  import unittest

  class EntitiesTest(unittest.TestCase):

      def test_positive_create_user(self):
          """Create a new user providing all expected attributes.

          :id: 1d73b8cc-a754-4637-8bae-d9d2aaf89003
          :expectedresults: User is successfully created
          :requirement: User Management
          :caseautomation: Automated
          :caselevel: Acceptance
          :casecomponent: CLI
          :testtype: Functional
          :caseimportance: High
          :upstream: No
          """
          user = entities.User(name='David', age=20)
          self.assertEqual(user.name, 'David')
          self.assertEqual(user.age, 20)

When the above test case is collected, Betelgeuse will make use of all 9 fields
provided and generates a more meaningful test case.

Ok, this is cool. But wait, there is more! Betelgeuse will reuse fields defined
in different levels, namely:

  - function level
  - class level
  - module level
  - package level

This feature can be leveraged to minimize the amount of information that needs
to be written for each test case. Since most of the time, test cases grouped in
a module usually share the same generic information, one could move most of
these fields to the ``module`` level and every single test case found by
Betelgeuse will inherit these attributes. For example:


.. code:: python

    """Test cases for entities.

    :caseautomation: Automated
    :casecomponent: CLI
    :caseimportance: High
    :caselevel: Acceptance
    :requirement: User Management
    :testtype: functional
    :upstream: no
    """

    import entities
    import unittest


    class EntitiesTest(unittest.TestCase):

        def test_positive_create_user(self):
            """Create a new user providing all expected attributes.

            :id: 1d73b8cc-a754-4637-8bae-d9d2aaf89003
            :expectedresults: User is successfully created
            """
            user = entities.User(name='David', age=20)
            self.assertEqual(user.name, 'David')
            self.assertEqual(user.age, 20)


        def test_positive_create_car(self):
            """Create a new car providing all expected attributes.

            :id: 71b9b000-b978-4a95-b6f8-83c09ed39c01
            :caseimportance: Medium
            :expectedresults: Car is successfully created and has no owner
            """
            car = entities.Car(make='Honda', year=2016)
            self.assertEqual(car.make, 'Honda')
            self.assertEqual(car.year, 2016)

Now all discovered test cases will inherit the attributes defined at the module
level. Furthermore, the test case attributes can be overridden at the *class
level* or at the *test case level*. Using the example above, since
``test_positive_create_car`` has its own *caseimportance* field defined,
Betelgeuse will use its value of *Medium* for this test case alone while all
other test cases will have a value of *High*, derived from the module.

Advanced Usage
==============

Betelgeuse allows configuring the field processing to your own needs, check the
:doc:`Betelgeuse Configuration Module <config>` documentation for more
information.
