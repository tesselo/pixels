import keyword
import operator
from functools import reduce

import numpy
from pyparsing import (
    Forward,
    Keyword,
    Literal,
    Optional,
    Regex,
    Word,
    ZeroOrMore,
    alphanums,
    delimitedList,
    oneOf,
)

from pixels.algebra import const


class RasterAlgebraException(Exception):
    pass


class FormulaParser(object):
    """
    Deconstruct mathematical algebra expressions and convert those into
    callable funcitons.


    Deconstruct mathematical algebra expressions and convert those into
    callable funcitons.

    This formula parser was inspired by the fourFun pyparsing example and also
    benefited from additional substantial contributions by Paul McGuire.
    This module uses pyparsing for this purpose and the parser is adopted from
    the `fourFun example`__.

    Example usage::

        >>> parser = FormulaParser()
        >>> parser.set_formula('log(a * 3 + b)')
        >>> parser.evaluate({'a': 5, 'b': 23})
        ... 3.6375861597263857
        >>> parser.evaluate({'a': [5, 6, 7], 'b': [23, 24, 25]})
        ... array([ 3.63758616,  3.73766962,  3.8286414 ])

    __ http://pyparsing.wikispaces.com/file/view/fourFn.py
    """

    def __init__(self):
        """
        Set up the Backus Normal Form (BNF) parser logic.
        """
        # Set an empty formula attribute
        self.formula = None

        # Instantiate blank parser for BNF construction
        self.bnf = Forward()

        # Expression for parenthesis, which are suppressed in the atoms
        # after matching.
        lpar = Literal(const.LPAR).suppress()
        rpar = Literal(const.RPAR).suppress()

        # Expression for mathematical constants: Euler number and Pi
        e = Keyword(const.EULER)
        pi = Keyword(const.PI)
        null = Keyword(const.NULL)
        _true = Keyword(const.TRUE)
        _false = Keyword(const.FALSE)

        # Prepare operator expressions
        addop = oneOf(const.ADDOP)
        multop = oneOf(const.MULTOP)
        powop = oneOf(const.POWOP)
        unary = reduce(operator.add, (Optional(x) for x in const.UNOP))

        # Expression for floating point numbers, allowing for scientific notation.
        number = Regex(const.NUMBER)

        # Variables are alphanumeric strings that represent keys in the input
        # data dictionary.
        variable = delimitedList(
            Word(alphanums), delim=const.VARIABLE_NAME_SEPARATOR, combine=True
        )

        # Functional calls
        function = Word(alphanums) + lpar + self.bnf + rpar

        # Atom core - a single element is either a math constant,
        # a function or a variable.
        atom_core = function | pi | e | null | _true | _false | number | variable

        # Atom subelement between parenthesis
        atom_subelement = lpar + self.bnf.suppress() + rpar

        # In atoms, pi and e need to be before the letters for it to be found
        atom = (
            unary + atom_core.setParseAction(self.push_first) | atom_subelement
        ).setParseAction(self.push_unary_operator)

        # By defining exponentiation as "atom [ ^ factor ]..." instead of
        # "atom [ ^ atom ]...", we get right-to-left exponents, instead of
        # left-to-right that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = Forward()
        factor << atom + ZeroOrMore((powop + factor).setParseAction(self.push_first))

        term = factor + ZeroOrMore((multop + factor).setParseAction(self.push_first))
        self.bnf << term + ZeroOrMore((addop + term).setParseAction(self.push_first))

    def push_first(self, strg, loc, toks):
        self.expr_stack.append(toks[0])

    def push_unary_operator(self, strg, loc, toks):
        """
        Set custom flag for unary operators.
        """
        if toks and toks[0] in const.UNARY_REPLACE_MAP:
            self.expr_stack.append(const.UNARY_REPLACE_MAP[toks[0]])

    def evaluate_stack(self, stack):
        """
        Evaluate a stack element.
        """
        op = stack.pop()

        if op in const.UNARY_OPERATOR_MAP:
            return const.UNARY_OPERATOR_MAP[op](self.evaluate_stack(stack))

        elif op in const.OPERATOR_MAP:
            op2 = self.evaluate_stack(stack)
            op1 = self.evaluate_stack(stack)
            # Handle null case
            if isinstance(op1, str) and op1 == const.NULL:
                op2 = self.get_mask(op2, op)
                op1 = True
            elif isinstance(op2, str) and op2 == const.NULL:
                op1 = self.get_mask(op1, op)
                op2 = True
            return const.OPERATOR_MAP[op](op1, op2)

        elif op in const.FUNCTION_MAP:
            return const.FUNCTION_MAP[op](self.evaluate_stack(stack))

        elif op in const.KEYWORD_MAP:
            return const.KEYWORD_MAP[op]

        elif op in self.variable_map:
            return self.variable_map[op]

        else:
            try:
                return numpy.array(op, dtype=const.ALGEBRA_PIXEL_TYPE_NUMPY)
            except ValueError:
                raise RasterAlgebraException(
                    'Found an undeclared variable "{0}" in formula.'.format(op)
                )

    @staticmethod
    def get_mask(data, operator):
        # Make sure the right operator is used
        if operator not in (const.EQUAL, const.NOT_EQUAL):
            raise RasterAlgebraException(
                'NULL can only be used with "==" or "!=" operators.'
            )
        # Get mask
        if numpy.ma.is_masked(data):
            return data.mask
        # If there is no mask, all values are not null
        return numpy.zeros(data.shape, dtype=numpy.bool)

    def set_formula(self, formula):
        """
        Store the input formula as the one to evaluate on.
        """
        # Remove any white space and line breaks from formula.
        self.formula = formula.replace(" ", "").replace("\n", "").replace("\r", "")

    def prepare_data(self):
        """
        Basic checks and conversion of input data.
        """
        for key, var in self.variable_map.items():
            # Keywords are not allowed as variables, variables can not start or
            # end with separator.
            if keyword.iskeyword(key) or key != key.strip(
                const.VARIABLE_NAME_SEPARATOR
            ):
                raise RasterAlgebraException(
                    'Invalid variable name found: "{}".'.format(key)
                )

            # Convert all data to numpy arrays
            if not isinstance(var, numpy.ndarray):
                with var.open() as rst:
                    self.variable_map[key] = rst.read().ravel()
            # Ensure all input data in the algebra pixel type.
            self.variable_map[key] = self.variable_map[key].astype(
                const.ALGEBRA_PIXEL_TYPE_NUMPY
            )

    def evaluate(self, data=None, formula=None):
        """
        Evaluate the input data using the current formula expression stack.

        The formula is stored as attribute and can be re-evaluated with several
        input data sets on an existing parser.
        """
        data = data or {}
        if formula:
            self.set_formula(formula)

        if not self.formula:
            raise RasterAlgebraException("Formula not specified.")

        # Store data for variables
        self.variable_map = data

        # Check and convert input data
        self.prepare_data()

        # Reset expression stack
        self.expr_stack = []

        # Populate the expression stack
        self.bnf.parseString(self.formula)

        # Evaluate stack on data
        return self.evaluate_stack(self.expr_stack)


def evaluate(formula, bands, stack):
    """
    Evaluate a formula based on a pixels stack and the data key lookup.


    Parameters
    ----------
    formula : str
        A raster algebra formula. The band keys in the formula should be from
        the list provided in the `bands` argument.
    bands : list or tuple
        A list of string band names. The band names should be in the same order
        as the first dimension in the `data` argument.
    stack : numpy array
        A 3D pixels stack to use for evaluation. The first dimension should be
        the bands, in the same order as in the `bands` list argument. The other
        two dimensions should be the width and the height.

    Returns
    -------
    result : numpy array
        A 2D array with the evaluated formula data.
    """
    parser = FormulaParser()
    parser.set_formula(formula)
    return parser.evaluate(dict(zip(bands, stack)))
