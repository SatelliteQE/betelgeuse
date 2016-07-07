Betelgeuse documentation
========================

.. contents:: Topics

.. _what_is_betelgeuse:

What is Betelgeuse?
```````````````````

Betelgeuse is a python program that reads standard Python test cases and offers
tools to interact with Polarion. Possible interactions are:

* Automatic creation/update of Requirements and Test Cases from a Python
  project code base.
* Automatic creation/update of Test Runs based on a jUnit XML file.

Betelgeuse uses `Testimony <https://pypi.python.org/pypi/testimony>`_ and
Pylarion projects to parse test cases and communicate with polarion
respectively.

.. _prerequisites:

Prerequisites
`````````````
Login to polarion in a browser to check if the login user has permissions to
create/update the following entities in Polarion:

* requirement
* test case
* test run

.. _quick_start:

Quick Start
```````````
1. Betelgeuse uses Pylarion to interact with polarion. Install Pylarion from its
   source.

   .. note::

     - It may be possible that the latest version of Betelgeuse may not work
       correctly with some versions of Pylarion.  In this case, please use an
       alternate working version of Pylarion.
     - Read Pylarion documentation and set up ``.pylarion`` config file as
       required.

2. Install betelguese from pypi.

   .. code-block:: bash

       $ pip install betelgeuse

3. Alternatively you can install from source:

   .. code-block:: bash

       $ git clone https://github.com/SatelliteQE/betelgeuse.git 
       $ cd betelgeuse
       $ pip install -e .

   .. note:: It is always recommended to use python virtual environment

.. _usage_examples:

Usage Examples
``````````````
.. note::

  1. For easy understanding of Betelgeuse, this repository is already included with
  ``sample_project`` folder.  This folder contains sample tests and XML results which
  will help in setting up and testing Betelgeuse for your project.  The sample
  commands used below also use this data.

  2. Always run the test runner and Betelgeuse on the same directory to make
  sure that the test run ID mapping works fine.  Otherwise Betelgeuse may
  report ID errors.  More info can be found in test_run_command_ section

.. _help_command:

help command
++++++++++++

.. code-block:: bash

    $ betelgeuse --help

.. _test_case_command:

test-case command
+++++++++++++++++
Creates/Updates test cases in polarion. This command performs the following
steps:

- Testimony is called to parse the test cases.
- For each parsed test case, the following actions are performed:

    - If ``$ID`` token is present in the test case, it is used as the test case
      id.  Or it is derived automatically based on the test Python import path.
    - Test case object is built based on different supplied test case tokens.
    - If ``@requirement`` token is present in the test case, it will be used as the
      requirement name.  Otherwise it is derived from the test module name.  For
      example, if the test module name is ``test_login_example``, then the
      requirement name is ``Login Example``.
    - The derived requirement name is queried in Polarion to check if it is
      already present.  Otherwise it is created.
    - The test case is queried with ``$ID`` token in Polarion.  If the test case
      is already present, it will be updated.  Otherwise, it will be created and
      linked to the requirement.

.. code-block:: bash

    $ betelgeuse test-case --path sample_project/tests/ PROJECT_CLOUD

    Creating test case test_login_1 for requirement: Login Example.
    Linking test case test_login_1 to requirement: Login Example.
    Fetching requirement Login Example.
    Creating requirement Login Example.

.. note::
  
  * ``PROJECT_CLOUD`` is the polarion project id and not the project name.  This
    can be found in Polarion -> Settings (icon) -> Administration -> ID.
  * ``path`` is the path of the folder which has the test cases source code.

.. warning::

   Are you not sure if you are using this command correctly? No problem! The
   test-case command can be used with ``--collect-only`` option which runs in a
   dry run mode and shows the changes it would have made wihtout actually making
   them:

     .. code-block:: bash

         $ betelgeuse test-case --path sample_project/tests/ PROJECT_CLOUD \
         --collect-only

         Creating test case test_login_1 for requirement: Login Example.
         Linking test case test_login_1 to requirement: Login Example.

.. _test_results_command:

test-results command
++++++++++++++++++++
Gives a nice summary of test cases/results in the given jUnit XML file.

.. code-block:: bash

    $ betelgeuse test-results --path \
    sample_project/results/sample-junit-result.xml

    Passed: 1

.. _test_run_command:

test-run command
++++++++++++++++
Creates/Updates a test run in polarion using the information in the given jUnit
XML file. This command performs the following steps:

- Parses the jUnit XML file to read all the test cases and their run statuses.
- Creates a new test run or updates an existing run with all the parsed test
  case items and their run statuses.

.. code-block:: bash

    $ betelgeuse test-run --path sample_project/results/sample-junit-result.xml \
    --test-run-id regression_test_run_1 --test-template-id Empty --user \
    testuser1 --source-code-path sample_project/tests/ PROJECT_CLOUD

    Test run regression_test_run_1 found.
    Adding test record for test case PROJECT_CLOUD-12655 with status passed.

At this time, it is very important to understand how Betelgeuse links the items
in the jUnit XML report to the actual source code.  To help in this process,
it is a must that both the test runner and Betelgeuse get called in the same
directory.  Consider the following jUnit XML report which just has one test case
for easy understanding:

.. code-block:: xml

    <testcase classname="sample_project.tests.test_login_example.LoginTestCase"
    file="sample_project/tests/test_login_example.py" line="421" name="test_login_1"
    time="694.768339396">...</testcase>

With the above report, Betelgeuse performs the following:

- Derives the test method's name by joining its ``classname`` and ``name``
  attributes with a dot.  In this case, it becomes
  ``sample_project.tests.test_login_example.LoginTestCase.test_login_1``.
- Looks at the ``--source-code-path`` option value and does the following:

    - converts every test  module path into a python import path.  For example:
      ``sample_project/tests/test_login_example.py`` will become
      ``sample_project.tests.test_login_example``.
    - All test methods or functions are then appended.  For example, the
      method ``test_login_1`` inside the class  ``LoginTestCase`` will be
      generated as
      ``sample_project.tests.test_login_example.LoginTestCase.test_login_1``.

- The information obtained from both the steps above are compared and ``@ID``
  token of the test method or function is identified.  This id is then queried
  against Polarion for a matching work item id (Polarion test case).  Once the
  work item id is identified, Betelgeuse will add the result for this test
  case work item id in the test run. 

.. warning::

  - If Betelgeuse is not able to find the ``@ID`` token for a test method, it
    will default to the Python import path. In our current example, it will be
    ``sample_project.tests.test_login_example.LoginTestCase.test_login_1``.
  - If no result is returned when querying Polarion for a matching test case,
    then the result will be skipped and the processing continues to the next
    test case in the jUnit XML file.  For this reason, it is highly recommended
    to run ``test-command`` command before ``test-run`` to make sure all
    required test cases are created/updated accordingly.
