r"""Parse ASCII tables.

Rows are pipe-separated cells:
>>> row.parse_strict("|Bob|21|")
['Bob', '21']

Padding is ignored:
>>> row.parse_strict("|  Bob  |  21  |")
['Bob', '21']

Outer borders are optional:
>>> row.parse_strict("Bob | 21")
['Bob', '21']

Body is many rows:
>>> body.parse_strict("\n".join([
... "Bob | 21",
... "Jim | 22",
... ]))
[['Bob', '21'], ['Jim', '22']]

Headers must be separated from the body:
>>> _ = table.parse_strict("\n".join([
... "Name | Age",
... "----------",
... "Bob  | 21 ",
... "Jim  | 22 ",
... ]))
>>> _ == [{'Name': 'Bob', 'Age': '21'}, {'Name': 'Jim', 'Age': '22'}]
True
"""
import parsec as P

def maybe(p):
    """Repeat a parser 0 or 1 times."""
    return P.times(p, 0, 1)

def _table(result):
    """Convert a parse result into a ``Table``."""
    (headers,), body = result
    # TODO: Ensure that headers and rows have the same number of columns
    #       in the parser.
    return [dict(zip(headers, row)) for row in body]

# TODO: Tidy these up.
csep = P.one_of("|")
padding = P.regex("[ \t]*")
content = P.regex("[^ |\n]([^|\n]*[^ |\n])?")
cell = padding.compose(content.skip(padding).parsecmap("".join))
row = maybe(csep).compose(P.separated(cell, csep, 2, end=False)).skip(maybe(csep))
rows = P.sepEndBy1(row, P.string("\n"))
body = rows
rsep = P.regex("[-+|]+\n?")
table = rsep.compose(P.separated(body, rsep, 2, 2).parsecmap(_table)).skip(rsep)

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS |
                                doctest.NORMALIZE_WHITESPACE |
                                doctest.REPORT_NDIFF)
