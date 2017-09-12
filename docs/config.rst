===============================
Betelgeuse Configuration Module
===============================

Betelgeuse ships with a :ref:`Default Configuration` which defines custom
fields, default values for some fields and some transformations.

You can configure Betelgeuse and provide your own custom fields, default values
and transformations by providing the ``--config-module`` option. The value of
``--config-module`` should be in Python path syntax, e.g.
``mycustom.config_module``. Note that the config module should be on the Python
`import search path`_.

Some custom fields are enumerations and expect some specific values. You can
check the :doc:`Custom fields' values choices <customfieldsvalues>` document
for a reference of the values allowed for some of the fields. Not all field
that are enumerations are listed on the document, only ones that are not
supposed to be customized.

.. note::

    Polarion allows each project to customize its own custom fields. If you
    find an error message while importing the test cases, first check if the
    value matches the case (choice values are casesensitive) and then check if
    you project has customized the enumeration for that field.

.. _import search path: http://www.diveintopython3.net/your-first-python-program.html#importsearchpath

Tutorial
========

In this tutorial shows how to create a configuration module which adds two more
custom fields by extending the default configuration custom fields list. In
addition to that, it will provide a default value for each added custom field
and a transformation function to do a final processing on the first added
field.

Let's start by creating a new file named ``my_custom_config.py``. Then the custom configuration can be added.

To provide two additional custom fields it will be required to read the custom
fields that ships with Betelgeuse and extend that with the new ones. The
Betelgeuse's default configuration can be accessed by importing the module
``betelgeuse.default_config``. Add the following content to the
``my_custom_config.py`` file:

.. code-block:: python

    from betelgeuse import default_config

    TESTCASE_CUSTOM_FIELDS = default_config.TESTCASE_CUSTOM_FIELDS + ['myfield1', 'myfield2']

By doing that and running ``betelgeuse --config-module my_custom_config
test-case ...`` will make Betelgeuse include ``myfield1`` and ``myfield2`` to
the generated XML if the test case docstring includes them.

The next step is to provide a default value for each added field. Betelgeuse
will look for a attribute called ``DEFAULT_{field_name.upper()}_VALUE`` for
each field and, if it is defined, the default value will then be evaluated. The
default value can be a plain string or a callable, for the latter it will be
called and a test case object will be passed, see `Testcase objects`_ for
information of available attributes.

The ``myfield1`` default value will be a plain string and the ``myfield2``
default value will be a callable that will return the current date. Add the
following lines to the ``my_custom_config.py`` file:

.. code-block:: python

    import datetime

    def get_default_myfield2(testcase):
        """Return the current date as string."""
        return str(datetime.date.today())


    DEFAULT_MYFIELD1_VALUE = 'custom value'
    DEFAULT_MYFIELD2_VALUE = get_default_myfield2

With that, whenever the added fields are not specified on a test case
docstring, the configured default values are going to be used.

In addition to custom values, a transformation function can be defined and that
will be after assigning all the field values. A transformation function is
useful, for example, to ensure lower or upper case on a value. Betelgeuse will
look for an attribute called ``TRANSFORM_{field_name.upper()}_VALUE`` on the
configuration module and if defined will call that function passing the value
and the testcase object, see `Testcase objects`_ for information of available
attributes.

Let's define a transformation function that will prefix the ``myfield1`` with
the value of ``myfield2``. Add the following lines to the
``my_custom_config.py`` file:

.. code-block:: python

    def prefix_with_myfield2_value(value, testcase):
        """Prefix the value with the value of myfield2 field."""
        return '{} {}'.format(testcase.fields['myfield2'], value)

    TRANSFORM_MYFIELD1_VALUE = prefix_with_myfield2_value

With that the needed configuration is in place and Betelgeuse can be run::

    betelgeuse --config-module betelgeuse_config test-case \
        sample_project/tests \
        PROJECT test-cases.xml

It will generate the ``test-cases.xml`` file and the added fields should be set
with the default values configured. It will use the default values since the
new fields are not defined on any of the ``sample_project`` test cases.

Default Configuration
=====================

The default configuration includes all the fields and custom fields that
Betelgeuse will look for when parsing the source code. It also provides the
default values and transformations for some of the fields.

.. note::

    The testcase fields are present on the configuration for information only.
    Each field requires specific processing, and because that, Betelgeuse won't
    be able to process additional fields.

    If you override the ``betelgeuse.default_config.TESTCASE_FIELDS`` and
    remove some of the fields they will not be processed and added to the
    generated XML. It is hightly recommended to avoid overriding or extending
    this configuration.

You can override or extend any of the defined information on your configuration
module. Make sure to use valid values or your import will fail since Betelgeuse
does not validate the values on Polarion.

.. literalinclude:: ../betelgeuse/default_config.py
    :linenos:

Testcase objects
================

.. autoclass:: betelgeuse.collector.TestFunction
    :members:
