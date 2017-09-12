Custom fields' values choices
=============================

The table below maps the custom fields which expect some specific values. For
`testtype`, `subtype1` and `subtype2` please refer to the next table.

+----------------+--------------------+
| Field          | Values             |
+================+====================+
| arch           | i386               |
|                +--------------------+
|                | x8664              |
|                +--------------------+
|                | ppc64              |
|                +--------------------+
|                | ppc64              |
|                +--------------------+
|                | s390x              |
|                +--------------------+
|                | ia64               |
+----------------+--------------------+
| caseautomation | automated          |
|                +--------------------+
|                | manualonly         |
|                +--------------------+
|                | notautomated       |
+----------------+--------------------+
| caseimportance | critical           |
|                +--------------------+
|                | high               |
|                +--------------------+
|                | medium             |
|                +--------------------+
|                | low                |
+----------------+--------------------+
| caselevel      | component [#f1]_   |
|                +--------------------+
|                | integration [#f2]_ |
|                +--------------------+
|                | system [#f3]_      |
|                +--------------------+
|                | acceptance [#f4]_  |
+----------------+--------------------+
| caseposneg     | positive           |
|                +--------------------+
|                | negative           |
+----------------+--------------------+
| upstream       | yes                |
|                +--------------------+
|                | no                 |
+----------------+--------------------+
| variant        | server             |
|                +--------------------+
|                | workstation        |
|                +--------------------+
|                | client             |
+----------------+--------------------+

The following table maps the values that can go with each `testtype`,
`subtype1` and `subtype2`. Depending on the value for one field only a limited
set of values can be used on the others fields.

+---------------+------------------+----------------+
| testtype      | subtype1         | subtype2       |
+===============+==================+================+
| functional    | \-               | \-             |
+---------------+------------------+----------------+
| nonfunctional | \-               | \-             |
+               +------------------+----------------+
|               | compliance       | 508            |
+               +                  +----------------+
|               |                  | commoncriteria |
+               +                  +----------------+
|               |                  | fips           |
+               +                  +----------------+
|               |                  | whql           |
+               +------------------+----------------+
|               | documentation    | help           |
+               +                  +----------------+
|               |                  | userguide      |
+               +------------------+----------------+
|               | i18nl10n         | \-             |
+               +------------------+----------------+
|               | installability   | \-             |
+               +------------------+----------------+
|               | interoperability | \-             |
+               +------------------+----------------+
|               | performance      | load [#f5]_    |
+               +                  +----------------+
|               |                  | stress [#f6]_  |
+               +------------------+----------------+
|               | reliability      | \-             |
+               +------------------+----------------+
|               | recoveryfailover | \-             |
+               +------------------+----------------+
|               | scalability      | \-             |
+               +------------------+----------------+
|               | usability        | \-             |
+---------------+------------------+----------------+
| structural    | \-               | \-             |
+---------------+------------------+----------------+

.. [#f1] Component testing (also known as unit, module or program testing)
    searches for defects in, and verifies the functioning of, software modules,
    programs, objects, classes, etc., that are separately testable.
.. [#f2] Integration testing tests interfaces between components, interactions
    with different parts of a system.
.. [#f3] In system testing, the test environment should correspond to the final
    target or production environment as much as possible in order to minimize
    the risk of environment-specific failures not being found in testing.
.. [#f4] The goal in acceptance testing is to establish confidence in the
    system, parts of the system or specific non-functional characteristics of
    the system.
.. [#f5] A type of performance testing conducted to evaluate the behavior of a
    component or system with increasing load, e.g. numbers of parallel users
    and/or numbers of transactions, to determine what load can be handled by
    the component or system.
.. [#f6] A type of performance testing conducted to evaluate a system or
    component at or beyond the limits of its anticipated or specified
    workloads, or with reduced availability of resources such as access to
    memory or servers.
