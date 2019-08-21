"""Generates source code from an AST.

Inpired by the ast.NodeVisitor and unparse.py (see
https://github.com/python/cpython/blob/master/Tools/parser/unparse.py)
"""
import ast
import io
import sys

# Large float and imaginary literals get turned into infinities in the AST.  We
# unparse those infinities to INFSTR.
INFSTR = '1e' + repr(sys.float_info.max_10_exp + 1)


class SourceGenerator():
    """Helper class to traverse the AST and generate the source code."""

    def __init__(self, node):
        """Make  the generated source code available on the ``source`` attr."""
        self._source = io.StringIO('')
        self._visit(node)
        self.source = self._source.getvalue()
        self._source.close()

    def _visit(self, node):
        visitor = getattr(self, f'_visit_{node.__class__.__name__}'.lower())
        visitor(node)

    def _iterate_seq(self, inter, f, seq):
        seq = iter(seq)
        try:
            f(next(seq))
        except StopIteration:
            pass
        else:
            for x in seq:
                inter()
                f(x)

    def _visit_attribute(self, node):
        self._visit(node.value)
        self._source.write(f'.{node.attr}')

    def _visit_call(self, node):
        self._visit(node.func)
        self._source.write('(')
        comma = False
        for arg in node.args:
            if comma:
                self._source.write(', ')
            else:
                comma = True
            self._visit(arg)
        for keyword in node.keywords:
            if comma:
                self._source.write(', ')
            else:
                comma = True
            self._visit(keyword)
        self._source.write(')')

    def _write_constant(self, value):
        if isinstance(value, (float, complex)):
            # Substitute overflowing decimal literal for AST infinities.
            self._source.write(repr(value).replace('inf', INFSTR))
        else:
            self._source.write(repr(value))

    def _visit_constant(self, t):
        value = t.value
        if isinstance(value, tuple):
            self.write('(')
            if len(value) == 1:
                self._write_constant(value[0])
                self.write(',')
            else:
                self._iterate_seq(
                    lambda: self._source.write(', '),
                    self._write_constant,
                    value
                )
            self.write(')')
        elif value is ...:
            self.write('...')
        else:
            if t.kind == 'u':
                self.write('u')
            self._write_constant(t.value)

    def _visit_name(self, node):
        self._source.write(node.id)

    def _visit_str(self, node):
        self._source.write(repr(node.s))

    def _visit_tuple(self, node):
        self._source.write('(')
        if len(node.elts) == 1:
            self._visit(node.elts[0])
            self._source.write(',')
        else:
            self._iterate_seq(
                lambda: self._source.write(', '), self._visit, node.elts)
        self._source.write(')')

    def _visit_bytes(self, node):
        self._source.write(repr(node.s))

    def _visit_joinedstr(self, node):
        self._source.write('f')
        string = io.StringIO()
        self._fstring_joinedstr(node, string.write)
        self._source.write(repr(string.getvalue()))

    def _fstring_joinedstr(self, node, write):
        for value in node.values:
            meth = getattr(self, f'_fstring_{type(value).__name__}'.lower())
            meth(value, write)

    def _fstring_str(self, node, write):
        value = node.s.replace('{', '{{').replace('}', '}}')
        write(value)

    def _fstring_constant(self, node, write):
        value = node.value.replace('{', '{{').replace('}', '}}')
        write(value)

    def _fstring_formattedvalue(self, node, write):
        write('{')
        expr = SourceGenerator(node.value).source
        if expr.startswith('{'):
            write(' ')  # Separate pair of opening brackets as "{ {"
        write(expr)
        if node.conversion != -1:
            conversion = chr(node.conversion)
            write(f'!{conversion}')
        if node.format_spec:
            write(':')
            meth = getattr(
                self, f'_fstring_{type(node.format_spec).__name__}'.lower())
            meth(node.format_spec, write)
        write('}')

    def _visit_nameconstant(self, node):
        self._source.write(repr(node.value))

    def _visit_num(self, node):
        # Substitute overflowing decimal literal for AST infinities.
        self._source.write(repr(node.n).replace('inf', INFSTR))

    def _visit_list(self, node):
        self._source.write('[')
        self._iterate_seq(
            lambda: self._source.write(', '), self._visit, node.elts)
        self._source.write(']')

    def _visit_listcomp(self, node):
        self._source.write('[')
        self._visit(node.elt)
        for gen in node.generators:
            self._visit(gen)
        self._source.write(']')

    def _visit_generatorexp(self, node):
        self._source.write('(')
        self._visit(node.elt)
        for gen in node.generators:
            self._visit(gen)
        self._source.write(')')

    def _visit_setcomp(self, node):
        self._source.write('{')
        self._visit(node.elt)
        for gen in node.generators:
            self._visit(gen)
        self._source.write('}')

    def _visit_dictcomp(self, node):
        self._source.write('{')
        self._visit(node.key)
        self._source.write(': ')
        self._visit(node.value)
        for gen in node.generators:
            self._visit(gen)
        self._source.write('}')

    def _visit_comprehension(self, node):
        self._source.write(' for ')
        self._visit(node.target)
        self._source.write(' in ')
        self._visit(node.iter)
        for if_clause in node.ifs:
            self._source.write(' if ')
            self._visit(if_clause)

    def _visit_ifexp(self, node):
        self._source.write('(')
        self._visit(node.body)
        self._source.write(' if ')
        self._visit(node.test)
        self._source.write(' else ')
        self._visit(node.orelse)
        self._source.write(')')

    def _visit_set(self, node):
        self._source.write('{')
        self._iterate_seq(
            lambda: self._source.write(', '), self._visit, node.elts)
        self._source.write('}')

    def _visit_dict(self, node):
        self._source.write('{')

        def write_key_value_pair(k, v):
            self._visit(k)
            self._source.write(': ')
            self._visit(v)

        def write_item(item):
            k, v = item
            if k is None:
                # for dictionary unpacking operator in dicts {**{'y': 2}} see
                # PEP 448 for details
                self._source.write('**')
                self._visit(v)
            else:
                write_key_value_pair(k, v)
        self._iterate_seq(
            lambda: self._source.write(', '),
            write_item,
            zip(node.keys, node.values)
        )
        self._source.write('}')

    unop = {'Invert': '~', 'Not': 'not', 'UAdd': '+', 'USub': '-'}

    def _visit_unaryop(self, node):
        self._source.write('(')
        self._source.write(self.unop[node.op.__class__.__name__])
        self._source.write(' ')
        self._visit(node.operand)
        self._source.write(')')

    binop = {
        'Add': '+', 'Sub': '-', 'Mult': '*', 'MatMult': '@', 'Div': '/', 'Mod':
        '%', 'LShift': '<<', 'RShift': '>>', 'BitOr': '|', 'BitXor': '^',
        'BitAnd': '&', 'FloorDiv': '//', 'Pow': '**'
    }

    def _visit_binop(self, node):
        self._source.write('(')
        self._visit(node.left)
        self._source.write(' ' + self.binop[node.op.__class__.__name__] + ' ')
        self._visit(node.right)
        self._source.write(')')

    cmpops = {
        'Eq': '==', 'NotEq': '!=', 'Lt': '<', 'LtE': '<=', 'Gt': '>', 'GtE':
        '>=', 'Is': 'is', 'IsNot': 'is not', 'In': 'in', 'NotIn': 'not in'
    }

    def _visit_compare(self, node):
        self._source.write('(')
        self._visit(node.left)
        for o, e in zip(node.ops, node.comparators):
            self._source.write(' ' + self.cmpops[o.__class__.__name__] + ' ')
            self._visit(e)
        self._source.write(')')

    boolops = {ast.And: 'and', ast.Or: 'or'}

    def _visit_boolop(self, node):
        self._source.write('(')
        s = f' {self.boolops[node.op.__class__]} '
        self._iterate_seq(
            lambda: self._source.write(s), self._visit, node.values)
        self._source.write(')')

    def _visit_subscript(self, node):
        self._visit(node.value)
        self._source.write('[')
        self._visit(node.slice)
        self._source.write(']')

    def _visit_starred(self, node):
        self._source.write('*')
        self._visit(node.value)

    def _visit_index(self, node):
        self._visit(node.value)

    def _visit_slice(self, node):
        if node.lower:
            self._visit(node.lower)
        self._source.write(':')
        if node.upper:
            self._visit(node.upper)
        if node.step:
            self._source.write(':')
            self._visit(node.step)

    def _visit_arg(self, node):
        self._source.write(node.arg)

    def _visit_arguments(self, node):
        first = True
        # normal arguments
        defaults = [None] * (len(node.args) - len(node.defaults))
        defaults = defaults + node.defaults
        for a, d in zip(node.args, defaults):
            if first:
                first = False
            else:
                self._source.write(', ')
            self._visit(a)
            if d:
                self._source.write('=')
                self._visit(d)

        # varargs, or bare '*' if no varargs but keyword-only arguments present
        if node.vararg or node.kwonlyargs:
            if first:
                first = False
            else:
                self._source.write(', ')
            self._source.write('*')
            if node.vararg:
                self._source.write(node.vararg.arg)
                if node.vararg.annotation:
                    self._source.write(': ')
                    self._visit(node.vararg.annotation)

        # keyword-only arguments
        if node.kwonlyargs:
            for a, d in zip(node.kwonlyargs, node.kw_defaults):
                if first:
                    first = False
                else:
                    self._source.write(', ')
                self._visit(a)
                if d:
                    self._source.write('=')
                    self._visit(d)

        # kwargs
        if node.kwarg:
            if first:
                first = False
            else:
                self._source.write(', ')
            self._source.write(f'**{node.kwarg.arg}')
            if node.kwarg.annotation:
                self._source.write(': ')
                self._visit(node.kwarg.annotation)

    def _visit_keyword(self, node):
        if node.arg is None:
            self._source.write('**')
        else:
            self._source.write(node.arg)
            self._source.write('=')
        self._visit(node.value)

    def _visit_lambda(self, node):
        self._source.write('(')
        self._source.write('lambda ')
        self._visit(node.args)
        self._source.write(': ')
        self._visit(node.body)
        self._source.write(')')


def gen_source(node):
    """Generate the source code based on the node AST."""
    return SourceGenerator(node).source
