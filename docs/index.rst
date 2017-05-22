Betelgeuse documentation
========================

.. contents:: Topics
    :local:


What is Betelgeuse?
```````````````````

Betelgeuse is a python program that reads standard Python test cases and offers
tools to interact with Polarion. Possible interactions are:

* Automatic creation/update of Requirements and Test Cases from a Python
  project code base.
* Automatic creation/update of Test Runs based on a jUnit XML file.

Betelgeuse uses Pylarion project to communicate with Polarion.

Prerequisites
`````````````

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
```````````

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
`````````````

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
+++++++++++++++++++++++++++++++++++++++++++

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
``````````````

.. note::

  1. For easy understanding of Betelgeuse, this repository is already included with
  ``sample_project`` folder. This folder contains sample tests and XML results which
  will help in setting up and testing Betelgeuse for your project. The sample
  commands used below also use this data.

  2. Always run the test runner and Betelgeuse on the same directory to make
  sure that the test run ID mapping works fine. Otherwise Betelgeuse may
  report ID errors. More info can be found in `test-run command`_ section

help command
++++++++++++

.. code-block:: console

    $ betelgeuse --help

test-case command
+++++++++++++++++

Creates/Updates test cases in Polarion. This command performs the following
steps:

- Walk a ``path`` and collect the test methods and functions defined on test
  modules. Test modules are the ones which name matches either ``test_*.py`` or
  ``*_test.py``.
- For each collected test, the following actions are performed:

    - If ``:id:`` field is present in the test case, it is used as the test case
      id. Or it is derived automatically based on the test Python import path.
    - If ``:requirement:`` field is present in the test docstring, it will be
      used as the requirement name. Otherwise it is derived from the test
      module name. For example, if the test module name is
      ``test_login_example``, then the requirement name is ``Login Example``.
    - Other fields are going to be populated if present on the test docstring.
    - The derived requirement name is queried in Polarion to check if it is
      already present. Otherwise it is created.
    - The test case is queried with ``:id:`` field in Polarion. If the test
      case is already present, it will be updated. Otherwise, it will be
      created and linked to the requirement.

.. code-block:: console

    $ betelgeuse test-case --path sample_project/tests/ PROJECT_CLOUD

    Creating test case test_login_1 for requirement: Login Example.
    Linking test case test_login_1 to requirement: Login Example.
    Fetching requirement Login Example.
    Creating requirement Login Example.

.. note::

  * ``PROJECT_CLOUD`` is the Polarion project id and not the project name. This
    can be found in Polarion -> Settings (icon) -> Administration -> ID.
  * ``path`` is the path of the folder which has the test cases source code.

.. warning::

   Are you not sure if you are using this command correctly? No problem! The
   test-case command can be used with ``--collect-only`` option which runs in a
   dry run mode and shows the changes it would have made wihtout actually making
   them:

     .. code-block:: console

         $ betelgeuse test-case --path sample_project/tests/ PROJECT_CLOUD \
         --collect-only

         Creating test case test_login_1 for requirement: Login Example.
         Linking test case test_login_1 to requirement: Login Example.

test-plan command
+++++++++++++++++

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
++++++++++++++++++++

Gives a nice summary of test cases/results in the given jUnit XML file.

.. code-block:: console

    $ betelgeuse test-results --path \
    sample_project/results/sample-junit-result.xml

    Passed: 1

test-run command
++++++++++++++++

Creates/Updates a test run in Polarion using the information in the given jUnit
XML file. This command performs the following steps:

- Parses the jUnit XML file to read all the test cases and their run statuses.
- Creates a new test run or updates an existing run with all the parsed test
  case items and their run statuses.

.. code-block:: console

    $ betelgeuse test-run --path sample_project/results/sample-junit-result.xml \
    --test-run-id regression_test_run_1 --test-template-id Empty --user \
    testuser1 --source-code-path sample_project/tests/ PROJECT_CLOUD

    Test run regression_test_run_1 found.
    Adding test record for test case PROJECT_CLOUD-12655 with status passed.

At this time, it is very important to understand how Betelgeuse links the items
in the jUnit XML report to the actual source code. To help in this process,
it is a must that both the test runner and Betelgeuse get called in the same
directory. Consider the following jUnit XML report which just has one test case
for easy understanding:

.. code-block:: xml

    <testcase classname="sample_project.tests.test_login_example.LoginTestCase"
    file="sample_project/tests/test_login_example.py" line="421" name="test_login_1"
    time="694.768339396">...</testcase>

With the above report, Betelgeuse performs the following:

- Derives the test method's name by joining its ``classname`` and ``name``
  attributes with a dot. In this case, it becomes
  ``sample_project.tests.test_login_example.LoginTestCase.test_login_1``.
- Looks at the ``--source-code-path`` option value and does the following:

    - converts every test module path into a python import path. For example:
      ``sample_project/tests/test_login_example.py`` will become
      ``sample_project.tests.test_login_example``.
    - All test methods or functions are then appended. For example, the
      method ``test_login_1`` inside the class ``LoginTestCase`` will be
      generated as
      ``sample_project.tests.test_login_example.LoginTestCase.test_login_1``.

- The information obtained from both the steps above are compared and ``:ID``
  field of the test method or function is identified. This id is then queried
  against Polarion for a matching work item id (Polarion test case). Once the
  work item id is identified, Betelgeuse will add the result for this test
  case work item id in the test run.

.. warning::

  - If Betelgeuse is not able to find the ``:ID`` field for a test method, it
    will default to the Python import path. In our current example, it will be
    ``sample_project.tests.test_login_example.LoginTestCase.test_login_1``.
  - If no result is returned when querying Polarion for a matching test case,
    then the result will be skipped and the processing continues to the next
    test case in the jUnit XML file. For this reason, it is highly recommended
    to run ``test-command`` command before ``test-run`` to make sure all
    required test cases are created/updated accordingly.

The test-run command allows setting custom fields in order to better define the
environment. There are two ways to define custom fields:

``key=value`` format
    This a shortcut when you want to define plain strings as the value of a
    custom field.

JSON format
    This approach suits better when the type of the custom field matters. For
    example, if a custom field expects a boolean as a value.

Example using ``key=value`` format:

.. code-block:: console

    $ betelgeuse test-run \
        --path sample_project/results/sample-junit-result.xml \
        --test-run-id regression_test_run_1 \
        --test-template-id Empty
        --user testuser1 \
        --source-code-path sample_project/tests/ \
        --custom-fields arch=x8664 \
        --custom-fields variant=server \
        PROJECT_CLOUD

Example using JSON format:

.. code-block:: console

    $ betelgeuse test-run \
        --path sample_project/results/sample-junit-result.xml \
        --test-run-id regression_test_run_1 \
        --test-template-id Empty
        --user testuser1 \
        --source-code-path sample_project/tests/ \
        --custom-fields '{"isautomated":true,"arch":"x8664"}' \
        PROJECT_CLOUD

.. warning::

    Make sure to pass the right value for the custom fields as Betelgeuse does
    not validate them. If an unexpected value is found, the command will fail
    with a stack trace showing the error.

xml-test-case command
+++++++++++++++++++++

The xml-test-case command generates an XML file suited to be imported by the
Test Case XML Importer. It reads the Python test suite source code and
generates a XML file with all the information necessary for the Test Case XML
Importer.

The xml-test-command command requires you to pass:

* The path to the Python test suite source code
* The Polarion project ID
* The output XML file path (it will override if the file already exists)

.. note::

    Even though ``--response-property`` is optional, it is highly recommended
    to pass it because will be easier to monitor the importer messages (which
    is not handled by Betelgeuse).

The example below shows how to run xml-test-case command:

.. code-block:: console

    $ betelgeuse xml-test-case \
        --automation-script-format "https://github.com/SatelliteQE/betelgeuse/tree/master/{path}#L{line_number}" \
        sample_project/tests \
        PROJECT \
        output.xml

xml-test-run command
++++++++++++++++++++

The xml-test-run command generates an XML file suited to be imported by the
Test Run XML importer. It takes:

* A valid xUnit XML file
* A Python test suite where test case IDs can be found

And generates a resulting XML file with all the information necessary for the
Test Run XML importer.

The xml-test-run command only requires you to pass:

* The path to the xUnit XML file
* The path to the Python test suite source code
* The Polarion user ID
* The Polarion project ID
* The output XML file path (it will override if the file already exists)

.. note::

    Even though ``--response-property`` is optional, it is highly recommended
    to pass it because will be easier to monitor the importer messages (which
    is not handled by Betelgeuse).

The example below shows how to run xml-test-run command:

.. code-block:: console

    $ betelgeuse xml-test-run \
        --response-property property_key=property_value \
        sample_project/results/sample-junit-result.xml \
        sample_project/tests/ \
        testuser \
        PROJECT \
        output.xml

The xml-test-run command can set test run custom fields.  The
``--custom-fields`` option can be used with a ``key=value`` format or a JSON
format as explained in `test-run command`_ section.

.. warning::

    Make sure to pass the the custom field ID (same as in Polarion) and its
    value. Make sure to pass custom field values as string since they will be
    converted to XML where there is no type information.

Case Study - A real world sample Test Case
```````````````````````````````````````````

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
