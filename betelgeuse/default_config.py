"""Default Betelgeuse configuration."""
from betelgeuse import parser


####################
# Helper functions #
####################

def _get_default_description(testcase):
    """Return the default value for description field."""
    return parser.parse_rst(testcase.docstring)


def _get_default_title(testcase):
    """Return the default value for title field."""
    return testcase.name


def _get_default_caseposneg(testcase):
    """Return the default value for caseposneg custom field."""
    return 'negative' if 'negative' in testcase.name.lower() else 'positive'


def _transform_to_lower(value, testcase):
    """Transform a field value to lower case."""
    return value.lower()


###################
# Testcase Fields #
###################

#: Default testcase fields
TESTCASE_FIELDS = (
    'approvers',
    'assignee',
    'description',
    'duedate',
    'expectedresults',
    'id',
    'initialestimate',
    'parametrized',
    'requirement',
    'status',
    'steps',
    'title',
)

#: Default testcase custom fields
TESTCASE_CUSTOM_FIELDS = (
    'arch',
    'automation_script',
    'caseautomation',
    'casecomponent',
    'caseimportance',
    'caselevel',
    'caseposneg',
    'setup',
    'subcomponent',
    'subtype1',
    'subtype2',
    'tags',
    'tcmsarguments',
    'tcmsbug',
    'tcmscaseid',
    'tcmscategory',
    'tcmscomponent',
    'tcmsnotes',
    'tcmsplan',
    'tcmsreference',
    'tcmsrequirement',
    'tcmsscript',
    'tcmstag',
    'teardown',
    'testtier',
    'testtype',
    'upstream',
    'variant',
)

########################
# Default field values #
########################

DEFAULT_CASEAUTOMATION_VALUE = 'automated'
DEFAULT_CASECOMPONENT_VALUE = '-'
DEFAULT_CASEIMPORTANCE_VALUE = 'medium'
DEFAULT_CASELEVEL_VALUE = 'component'
DEFAULT_CASEPOSNEG_VALUE = _get_default_caseposneg
DEFAULT_DESCRIPTION_VALUE = _get_default_description
DEFAULT_PARAMETRIZED_VALUE = 'no'
DEFAULT_SUBTYPE1_VALUE = '-'
DEFAULT_TESTTYPE_VALUE = 'functional'
DEFAULT_TITLE_VALUE = _get_default_title
DEFAULT_UPSTREAM_VALUE = 'no'

####################################
# Value transformation definitions #
####################################

TRANSFORM_CASEAUTOMATION_VALUE = _transform_to_lower
TRANSFORM_CASECOMPONENT_VALUE = _transform_to_lower
TRANSFORM_CASEIMPORTANCE_VALUE = _transform_to_lower
TRANSFORM_CASELEVEL_VALUE = _transform_to_lower
TRANSFORM_CASEPOSNEG_VALUE = _transform_to_lower
TRANSFORM_PARAMETRIZED_VALUE = _transform_to_lower
TRANSFORM_SUBTYPE1_VALUE = _transform_to_lower
TRANSFORM_TESTTYPE_VALUE = _transform_to_lower
TRANSFORM_UPSTREAM_VALUE = _transform_to_lower
