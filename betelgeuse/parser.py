"""Parsers for test docstrings."""
from collections import namedtuple
from io import StringIO
from xml.dom import minidom

from docutils.core import publish_parts
from docutils.parsers.rst import nodes, roles
from docutils.readers import standalone
from docutils.transforms import frontmatter
from docutils.writers import html5_polyglot as writer


RSTParseMessage = namedtuple('RSTParseMessage', 'line level message')


class TableFieldListTranslator(writer.HTMLTranslator):
    """An HTML 5 translator which creates field lists as HTML tables."""

    def visit_field_list(self, node):
        """Open the field list."""
        # Keep simple paragraphs in the field_body to enable CSS
        # rule to start body on new line if the label is too long
        classes = 'field-list'
        if (self.is_compactable(node)):
            classes += ' simple'
        self.body.append(self.starttag(node, 'table', CLASS=classes))

    def depart_field_list(self, node):
        """Close the field list."""
        self.body.append('</table>\n')

    def visit_field(self, node):
        """Open field."""
        self.body.append(self.starttag(
            node, 'tr', '', CLASS=''.join(node.parent['classes'])))

    def depart_field(self, node):
        """Close field."""
        self.body.append('</tr>\n')

    # as field is ignored, pass class arguments to field-name and field-body:

    def visit_field_name(self, node):
        """Open field name."""
        self.body.append(self.starttag(
            node, 'th', '', CLASS=''.join(node.parent['classes'])))

    def depart_field_name(self, node):
        """Close field name."""
        self.body.append('</th>\n')

    def visit_field_body(self, node):
        """Open field body."""
        self.body.append(self.starttag(
            node, 'td', '', CLASS=''.join(node.parent['classes'])))
        # prevent misalignment of following content if the field is empty:
        if not node.children:
            self.body.append('<p></p>')

    def depart_field_body(self, node):
        """Close field body."""
        self.body.append('</td>\n')


class HTMLWriter(writer.Writer):
    """HTML writer which allows customizing the translator_class."""

    def __init__(self, translator_class=None):
        """Initialize the writer and set the translator_class."""
        writer.Writer.__init__(self)
        if translator_class is None:
            translator_class = writer.HTMLTranslator
        self.translator_class = translator_class


class NoDocInfoReader(standalone.Reader):
    """Reader that does not do the DocInfo transformation.

    Extend standalone reader and drop the DocInfo transformation. Without that
    transformation, the first field list element will remain a field list and
    won't be converted to a docinfo element.
    """

    def get_transforms(self):
        """Get default transforms without DocInfo."""
        transforms = standalone.Reader.get_transforms(self)
        transforms.remove(frontmatter.DocInfo)
        return transforms


def _register_roles():
    """Register Python roles that Sphinx supports."""
    for role in (
            'data', 'exc', 'func', 'class', 'const', 'attr', 'meth', 'mod',
            'obj'
    ):
        roles.register_generic_role(role, nodes.raw)
        roles.register_generic_role('py:' + role, nodes.raw)


def parse_rst(string, translator_class=None):
    """Parse a RST formatted string into HTML."""
    if not string:
        return ''
    if not hasattr(_register_roles, '_roles_registered'):
        _register_roles()
        _register_roles._roles_registered = True

    warning_stream = StringIO()
    parts = publish_parts(
        string,
        reader=NoDocInfoReader(),
        settings_overrides={
            'embed_stylesheet': False,
            'input_encoding': 'utf-8',
            'syntax_highlight': 'short',
            'warning_stream': warning_stream,
        },
        writer=HTMLWriter(translator_class=translator_class),
    )

    rst_parse_messages = []
    for warning in warning_stream.getvalue().splitlines():
        if not warning or ':' not in warning:
            continue
        warning = warning.split(' ', 2)
        rst_parse_messages.append(RSTParseMessage(
            line=warning[0].split(':')[1],
            level=warning[1].split('/')[0][1:].lower(),
            message=warning[2],
        ))
    warning_stream.close()

    # TODO: decide what to do with the rst parser warnings and errors
    return parts['html_body']


def parse_docstring(docstring=None):
    """Parse the docstring and return captured fields.

    For example in the following docstring (using single quote to demo)::

        '''Docstring content.

        More docstring content.

        :field1: value1
        :field2: value2
        :field3: value3
        '''

    Will return a dict with the following content::

        {
            'field1': 'value1',
            'field2': 'value2',
            'field3': 'value3',
        }
    """
    if not docstring:
        return {}

    fields_dict = {}
    parsed_docstring = parse_rst(docstring)
    if isinstance(parsed_docstring, type(u'')):
        parsed_docstring = parsed_docstring.encode('utf-8')
    document = minidom.parseString(parsed_docstring)
    field_lists = [
        element for element in document.getElementsByTagName('dl')
        if element.attributes.get('class') and
        'field-list' in element.attributes.get('class').value
    ]
    for field_list in field_lists:
        field_names = field_list.getElementsByTagName('dt')
        field_values = field_list.getElementsByTagName('dd')
        for field_name, field_value in zip(field_names, field_values):
            field_name = field_name.firstChild.nodeValue.lower()
            output = ''
            if (len(field_value.childNodes) == 2 and
                    field_value.childNodes[0].tagName == 'p'):
                # childNodes will have two items because the first item will be
                # an element and the second item will be a text u'\n'
                output = field_value.childNodes[0].firstChild.nodeValue
            else:
                for node in field_value.childNodes:
                    output += node.toxml()
            field_value = output
            fields_dict[field_name] = field_value
    return fields_dict
